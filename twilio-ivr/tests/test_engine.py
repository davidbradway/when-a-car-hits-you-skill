import os
import sys

os.environ.setdefault("VALIDATE_TWILIO_SIGNATURE", "false")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from twilio.request_validator import RequestValidator

import app as flask_app_module
from ivr import config, state


@pytest.fixture
def client():
    flask_app_module.app.config["TESTING"] = True
    with flask_app_module.app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def clear_sessions():
    state._sessions.clear()
    yield
    state._sessions.clear()


def start_call(client, call_sid="CA123", from_number="+15551234567"):
    return client.post("/voice", data={"CallSid": call_sid, "From": from_number})


def answer(client, step_id, call_sid="CA123", digits=None):
    data = {"CallSid": call_sid}
    if digits is not None:
        data["Digits"] = digits
    return client.post(f"/gather/{step_id}", data=data)


def test_voice_starts_with_nc_question(client):
    resp = start_call(client)
    assert resp.status_code == 200
    assert b"Press 1 if the crash happened in North Carolina" in resp.data


def continue_to_end(client, call_sid="CA123"):
    """Press 2 until the advice sections run out; returns the final response."""
    for _ in range(20):
        resp = answer(client, "section", call_sid=call_sid, digits="2")
        if b"Press 1 to hear that again" not in resp.data:
            return resp
    raise AssertionError("advice sections never ended")


def test_nc_caller_hears_first_nc_section_with_repeat_menu(client):
    start_call(client)
    resp = answer(client, "nc_check", digits="1")
    body = resp.data.decode()
    assert "not legal, medical, or financial advice" in body
    assert "Part 1 of 5" in body
    assert "pure contributory negligence" in body
    # Only one section at a time.
    assert "Report the crash, wait for police" not in body
    assert "Press 1 to hear that again. Press 2 to continue." in body
    assert 'action="/gather/section"' in body


def test_continue_advances_through_every_nc_section_then_offers_transfer(client):
    start_call(client)
    answer(client, "nc_check", digits="1")
    heard = []
    for _ in range(4):
        heard.append(answer(client, "section", digits="2").data.decode())
    assert "Part 2 of 5" in heard[0] and "med pay" in heard[0]
    assert "Part 3 of 5" in heard[1] and "Report the crash, wait for police" in heard[1]
    assert "Part 4 of 5" in heard[2]
    assert "Part 5 of 5" in heard[3] and "track your losses" in heard[3]
    resp = answer(client, "section", digits="2")
    assert b"Press 1 to be connected now to the Law Office of Johnson and Groninger" in resp.data


def test_repeat_rereads_the_same_section(client):
    start_call(client)
    answer(client, "nc_check", digits="1")
    answer(client, "section", digits="2")  # on to part 2
    resp = answer(client, "section", digits="1")
    body = resp.data.decode()
    assert "Part 2 of 5" in body
    assert "med pay" in body
    # The disclaimer is read once, at the start, not on every repeat.
    assert "not legal, medical, or financial advice" not in body
    resp = answer(client, "section", digits="2")
    assert b"Part 3 of 5" in resp.data


def test_non_nc_caller_hears_general_sections_only_and_call_ends(client):
    start_call(client)
    resp = answer(client, "nc_check", digits="2")
    body = resp.data.decode()
    assert "pure contributory negligence" not in body
    assert "Part 1 of 3" in body
    assert "Report the crash, wait for police" in body
    resp = continue_to_end(client)
    body = resp.data.decode()
    assert "Johnson and Groninger" not in body
    assert "Take care of yourself. Goodbye." in body
    assert "<Hangup" in body


def test_section_bad_input_reasks_menu_then_continues(client):
    start_call(client)
    answer(client, "nc_check", digits="2")
    resp = answer(client, "section", digits="9")
    body = resp.data.decode()
    assert "Sorry, I didn" in body
    assert "Press 1 to hear that again" in body
    # Re-asks just the menu, not the whole section.
    assert "Report the crash" not in body
    answer(client, "section")  # silence
    resp = answer(client, "section")  # retries exhausted: default is continue
    assert b"Part 2 of 3" in resp.data


def test_section_retry_budget_resets_after_a_valid_press(client):
    start_call(client)
    answer(client, "nc_check", digits="2")
    answer(client, "section", digits="9")
    answer(client, "section", digits="9")
    answer(client, "section", digits="2")  # valid: on to part 2
    resp = answer(client, "section", digits="9")
    # A fresh section gets a fresh retry budget rather than auto-continuing.
    assert b"Sorry, I didn" in resp.data


def test_transfer_accepted_dials_the_law_office(client):
    start_call(client)
    answer(client, "nc_check", digits="1")
    continue_to_end(client)
    resp = answer(client, "transfer", digits="1")
    body = resp.data.decode()
    assert "+19192834372" in body
    assert "<Dial" in body


def test_transfer_declined_ends_the_call(client):
    start_call(client)
    answer(client, "nc_check", digits="1")
    continue_to_end(client)
    resp = answer(client, "transfer", digits="2")
    body = resp.data.decode()
    assert "Take care of yourself. Goodbye." in body
    assert "<Dial" not in body
    assert "<Hangup" in body


def test_invalid_dtmf_retries_then_falls_back_to_default(client):
    start_call(client)
    resp = answer(client, "nc_check", digits="9")
    assert b"Sorry, I didn" in resp.data
    resp = answer(client, "nc_check", digits="9")
    # Second bad digit still within retry budget (MAX_RETRIES_PER_STEP=2)
    assert b"Sorry, I didn" in resp.data
    resp = answer(client, "nc_check", digits="9")
    # Retries exhausted: falls back to the default ("no") and moves on.
    body = resp.data.decode()
    assert "pure contributory negligence" not in body
    assert "Part 1 of 3" in body


# ---------------------------------------------------------------------------
# Deployment behaviour: reverse proxy, signature handling, health, retention
# ---------------------------------------------------------------------------

PUBLIC_URL = "https://crashline.example.com/voice"


def test_signature_validates_against_public_url_behind_proxy(client, monkeypatch):
    """Twilio signs the PUBLIC https URL, but behind a TLS-terminating proxy
    Flask sees http://localhost/voice. Without ProxyFix the two never match and
    every webhook 403s — the app looks completely dead with no obvious cause.
    """
    token = "test_auth_token"
    monkeypatch.setattr(config, "VALIDATE_TWILIO_SIGNATURE", True)
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", token)

    params = {"CallSid": "CA_proxy", "From": "+15550000000"}
    signature = RequestValidator(token).compute_signature(PUBLIC_URL, params)

    resp = client.post(
        "/voice",
        data=params,
        headers={
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "crashline.example.com",
            "X-Twilio-Signature": signature,
        },
    )
    assert resp.status_code == 200


def test_signature_rejected_when_url_does_not_match(client, monkeypatch):
    """The same signature without the proxy headers must fail — proving the
    check is genuinely bound to the URL and the test above is not a no-op.
    """
    token = "test_auth_token"
    monkeypatch.setattr(config, "VALIDATE_TWILIO_SIGNATURE", True)
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", token)

    params = {"CallSid": "CA_proxy", "From": "+15550000000"}
    signature = RequestValidator(token).compute_signature(PUBLIC_URL, params)

    resp = client.post("/voice", data=params, headers={"X-Twilio-Signature": signature})
    assert resp.status_code == 403


def test_validation_fails_closed_when_token_is_missing(client, monkeypatch):
    """An empty token used to silently disable validation entirely, so one typo
    in .env would leave these endpoints open to anyone who can send a POST.
    """
    monkeypatch.setattr(config, "VALIDATE_TWILIO_SIGNATURE", True)
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", "")

    resp = client.post("/voice", data={"CallSid": "CA_x", "From": "+15550000000"})
    assert resp.status_code == 500


def test_healthz_is_unauthenticated_and_reports_the_running_commit(client, monkeypatch):
    monkeypatch.setattr(config, "GIT_SHA", "deadbeef")
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "commit": "deadbeef"}


def test_abandoned_sessions_are_swept(client):
    """An abandoned call's session should not live forever in a long-running
    process.
    """
    start_call(client, call_sid="CA_old")
    assert "CA_old" in state._sessions

    state._sessions["CA_old"].started_monotonic -= state.SESSION_TTL_SECONDS + 1
    start_call(client, call_sid="CA_new")

    assert "CA_old" not in state._sessions
    assert "CA_new" in state._sessions
