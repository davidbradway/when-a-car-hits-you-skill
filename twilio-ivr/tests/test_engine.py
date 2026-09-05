import os
import sys

os.environ.setdefault("VALIDATE_TWILIO_SIGNATURE", "false")
os.environ.setdefault("SMTP_USER", "")
os.environ.setdefault("SMTP_PASSWORD", "")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import app as flask_app_module
from ivr import mailer, state


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


@pytest.fixture
def sent_emails(monkeypatch):
    sent = []

    def fake_send_email(subject, body):
        sent.append((subject, body))

    monkeypatch.setattr(mailer, "send_email", fake_send_email)
    return sent


def start_call(client, call_sid="CA123", from_number="+15551234567"):
    return client.post("/voice", data={"CallSid": call_sid, "From": from_number})


def answer(client, step_id, call_sid="CA123", digits=None, speech=None):
    data = {"CallSid": call_sid}
    if digits is not None:
        data["Digits"] = digits
    if speech is not None:
        data["SpeechResult"] = speech
    return client.post(f"/gather/{step_id}", data=data)


def test_voice_starts_at_phase_question(client):
    resp = start_call(client)
    assert resp.status_code == 200
    assert b"Press 1 if you are still at the scene" in resp.data


def test_emergency_symptoms_short_circuits_to_report(client, sent_emails):
    start_call(client)
    answer(client, "phase", digits="1")
    resp = answer(client, "emergency", digits="1")
    assert b"call 911" in resp.data.lower()
    assert len(sent_emails) == 1
    subject, body = sent_emails[0]
    assert subject.startswith("URGENT crash report")
    assert "SEVERE SYMPTOMS" in body


def test_invalid_dtmf_retries_then_falls_back_to_default(client):
    start_call(client)
    resp = answer(client, "phase", digits="9")
    assert b"Sorry, I didn" in resp.data
    resp = answer(client, "phase", digits="9")
    # Second bad digit still within retry budget (MAX_RETRIES_PER_STEP=2)
    assert b"Sorry, I didn" in resp.data
    resp = answer(client, "phase", digits="9")
    # Retries exhausted: falls back to default and moves on to emergency check.
    assert b"loss of consciousness" in resp.data


def test_phase_guidance_reads_guidance_and_offers_repeat(client):
    start_call(client)
    answer(client, "phase", digits="2")
    resp = answer(client, "emergency", digits="2")
    assert b"Here is what to keep in mind" in resp.data
    assert b"adrenaline masks injuries" in resp.data
    assert b"Press 1 to hear this again" in resp.data


def test_phase_guidance_repeat_loops_back_to_itself(client):
    start_call(client)
    answer(client, "phase", digits="2")
    answer(client, "emergency", digits="2")
    resp = answer(client, "phase_guidance", digits="1")
    assert b"Here is what to keep in mind" in resp.data
    assert b"Press 1 to hear this again" in resp.data


def test_at_scene_skips_expenses_question(client, sent_emails):
    start_call(client)
    answer(client, "phase", digits="1")
    answer(client, "emergency", digits="2")
    answer(client, "phase_guidance", digits="2")
    answer(client, "datetime_location", speech="just now on Main Street")
    answer(client, "mode", digits="1")
    answer(client, "state_location", speech="North Carolina")
    answer(client, "police", digits="1")
    answer(client, "driver_info", digits="1")
    answer(client, "photos", digits="1")
    answer(client, "witnesses", digits="3")
    answer(client, "driver_behavior", digits="1")
    answer(client, "medical_care", digits="1")
    answer(client, "injuries", speech="sore knee")
    answer(client, "insurer_contacted", digits="2")
    answer(client, "settlement_offered", digits="2")
    resp = answer(client, "own_insurer_notified", digits="2")

    assert len(sent_emails) == 1
    assert "I've emailed your full crash summary report" in resp.data.decode()


def test_full_happy_path_sends_report(client, sent_emails):
    start_call(client)
    answer(client, "phase", digits="2")
    answer(client, "emergency", digits="2")
    answer(client, "phase_guidance", digits="2")
    answer(client, "datetime_location", speech="yesterday afternoon on Main Street in Durham")
    answer(client, "mode", digits="1")
    answer(client, "state_location", speech="North Carolina")
    answer(client, "police", digits="1")
    answer(client, "driver_info", digits="1")
    answer(client, "photos", digits="1")
    answer(client, "witnesses", digits="3")
    answer(client, "driver_behavior", digits="1")
    answer(client, "medical_care", digits="1")
    answer(client, "injuries", speech="sore knee and a scraped elbow")
    answer(client, "insurer_contacted", digits="2")
    answer(client, "settlement_offered", digits="2")
    answer(client, "own_insurer_notified", digits="2")
    resp = answer(client, "expenses", speech="one hundred dollars for a doctor visit")

    assert len(sent_emails) == 1
    subject, body = sent_emails[0]
    assert subject.startswith("Crash summary report")
    assert "North Carolina specifics" in body
    assert "Ann Groninger" in body
    assert "Durham Police non-emergency" in body
    assert "I've emailed your full crash summary report" in resp.data.decode()
