"""Flask app exposing the Twilio voice webhook for the crash line.

Point a Twilio phone number's "A call comes in" webhook at POST /voice.
See README.md for setup.

The call asks one question — was the crash in North Carolina? — reads the
matching advice, and, for North Carolina callers, offers a live transfer to
the Law Office of Johnson & Groninger, PLLC.
"""
import logging
from functools import wraps
from typing import Optional

from flask import Flask, request, abort
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse, Gather
from werkzeug.middleware.proxy_fix import ProxyFix

from ivr import config
from ivr.advice import GOODBYE, TRANSFER_NUMBER, TRANSFER_SAY, advice_for
from ivr.state import CallSession, drop, get, get_or_create
from ivr.steps import STEPS, Step

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# In production this app runs behind a TLS-terminating reverse proxy, so Flask
# sees "http://127.0.0.1:8000/voice" while Twilio computed its signature over
# "https://<public-host>/voice". Since validation below hashes request.url,
# without this every single webhook would fail and return 403.
#
# Exactly ONE proxy hop is trusted. Increasing these counts would let a caller
# forge X-Forwarded-* headers and therefore choose the URL that signatures are
# verified against. When run directly (no proxy) the headers are absent and
# this is a no-op.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


def validate_twilio_request(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # The explicit opt-out stays, for local testing and the test suite.
        if not config.VALIDATE_TWILIO_SIGNATURE:
            return f(*args, **kwargs)

        # Fail CLOSED when validation is enabled but no token is configured.
        # Previously an empty token silently skipped validation, so a single
        # typo in .env would leave these endpoints accepting unsigned requests
        # from anyone on the internet — while the config still claimed
        # validation was on.
        if not config.TWILIO_AUTH_TOKEN:
            logger.error(
                "VALIDATE_TWILIO_SIGNATURE is enabled but TWILIO_AUTH_TOKEN is empty. "
                "Refusing the request rather than serving it unverified. "
                "For local testing without a Twilio account, set "
                "VALIDATE_TWILIO_SIGNATURE=false."
            )
            abort(500)

        validator = RequestValidator(config.TWILIO_AUTH_TOKEN)
        signature = request.headers.get("X-Twilio-Signature", "")
        if not validator.validate(request.url, request.form, signature):
            logger.warning("Rejected request with invalid Twilio signature from %s", request.remote_addr)
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _gather_url(step_id: str) -> str:
    return f"/gather/{step_id}"


def render_step(step: Step, session: CallSession, prefix: str = "") -> VoiceResponse:
    vr = VoiceResponse()
    session.current_step = step.id
    gather = Gather(
        action=_gather_url(step.id), method="POST", input="dtmf", numDigits=step.num_digits, timeout=8,
    )
    gather.say(prefix + step.prompt(session), voice=config.VOICE)
    vr.append(gather)
    # No input received: loop back to the same step (handled in the /gather route).
    vr.redirect(_gather_url(step.id), method="POST")
    return vr


def _resolve_digit(step: Step, session: CallSession) -> Optional[str]:
    """Stores the caller's answer and returns it, or None if the step needs
    to be re-prompted (bad or missing input, with retries still available).

    When retries are exhausted, the step's default is stored instead, so the
    call always keeps moving even if the caller never presses a valid digit.
    """
    raw_value = request.form.get("Digits")
    parsed = step.digit_map.get(raw_value) if raw_value else None

    if parsed is not None:
        session.answers[step.field] = parsed
        return parsed

    retries = session.retries.get(step.id, 0)
    if retries >= config.MAX_RETRIES_PER_STEP:
        session.answers[step.field] = step.skip_default
        return step.skip_default

    session.retries[step.id] = retries + 1
    return None


@app.route("/")
def home():
    return "Hello, World!"


@app.get("/healthz")
def healthz():
    """Liveness and version probe.

    Deliberately unauthenticated: the container HEALTHCHECK and the deploy
    workflow both need to reach it without Twilio credentials. It exposes only
    the commit that is running — which is already public in the repo — and no
    call data.

    GIT_SHA is baked in at image build time, which is what lets a deploy prove
    the new code actually went live rather than assuming a push succeeded.
    """
    return {"status": "ok", "commit": config.GIT_SHA}, 200


@app.post("/voice")
@validate_twilio_request
def voice():
    call_sid = request.form.get("CallSid", "")
    from_number = request.form.get("From", "")
    session = get_or_create(call_sid, from_number)
    vr = render_step(STEPS["nc_check"], session)
    return str(vr), 200, {"Content-Type": "text/xml"}


@app.post("/gather/nc_check")
@validate_twilio_request
def gather_nc_check():
    call_sid = request.form.get("CallSid", "")
    session = get(call_sid)
    step = STEPS["nc_check"]
    if session is None:
        # Session expired or unknown — restart the call cleanly.
        session = get_or_create(call_sid, request.form.get("From", ""))
        vr = render_step(step, session)
        return str(vr), 200, {"Content-Type": "text/xml"}

    answer = _resolve_digit(step, session)
    if answer is None:
        vr = render_step(step, session, prefix=step.retry_prompt + " ")
        return str(vr), 200, {"Content-Type": "text/xml"}

    in_nc = answer == "yes"
    advice_text = advice_for(in_nc)

    if in_nc:
        vr = render_step(STEPS["transfer"], session, prefix=advice_text + " ")
    else:
        vr = VoiceResponse()
        vr.say(advice_text + " " + GOODBYE, voice=config.VOICE)
        vr.hangup()
        drop(call_sid)
    return str(vr), 200, {"Content-Type": "text/xml"}


@app.post("/gather/transfer")
@validate_twilio_request
def gather_transfer():
    call_sid = request.form.get("CallSid", "")
    session = get(call_sid)
    step = STEPS["transfer"]
    if session is None:
        # Session expired or unknown — restart the call cleanly.
        session = get_or_create(call_sid, request.form.get("From", ""))
        vr = render_step(STEPS["nc_check"], session)
        return str(vr), 200, {"Content-Type": "text/xml"}

    answer = _resolve_digit(step, session)
    if answer is None:
        vr = render_step(step, session, prefix=step.retry_prompt + " ")
        return str(vr), 200, {"Content-Type": "text/xml"}

    vr = VoiceResponse()
    if answer == "transfer":
        vr.say(TRANSFER_SAY, voice=config.VOICE)
        vr.dial(TRANSFER_NUMBER)
    else:
        vr.say(GOODBYE, voice=config.VOICE)
        vr.hangup()
    drop(call_sid)
    return str(vr), 200, {"Content-Type": "text/xml"}


if __name__ == "__main__":
    app.run(port=5000, debug=True)
