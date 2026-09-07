"""Flask app exposing the Twilio voice webhooks for the crash-report IVR.

Point a Twilio phone number's "A call comes in" webhook at POST /voice, and
(optionally) its "Call status changes" webhook at POST /status so an
abandoned call still emails whatever was collected. See README.md for setup.
"""
import logging
from functools import wraps

from flask import Flask, request, abort
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse, Gather
from werkzeug.middleware.proxy_fix import ProxyFix

from ivr import config, mailer, report
from ivr.state import CallSession, drop, get, get_or_create
from ivr.steps import REPORT, STEPS, Step

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
    gather_kwargs = dict(action=_gather_url(step.id), method="POST", timeout=8)
    if step.input_type == "dtmf":
        gather_kwargs.update(input="dtmf", numDigits=step.num_digits)
    else:
        gather_kwargs.update(input="speech", speechTimeout="auto")

    gather = Gather(**gather_kwargs)
    gather.say(prefix + step.prompt(session), voice=config.VOICE)
    vr.append(gather)
    # No input received: loop back to the same step (handled in the /gather route).
    vr.redirect(_gather_url(step.id), method="POST")
    return vr


def finish_call(session: CallSession) -> VoiceResponse:
    vr = VoiceResponse()
    closing = report.build_closing_speech(session)
    vr.say(closing, voice=config.VOICE)
    vr.hangup()

    if not session.reported:
        try:
            mailer.send_email(report.build_subject(session), report.build_report_text(session))
        except Exception:
            logger.exception("Failed to send crash report email for call %s", session.call_sid)
        session.reported = True
    drop(session.call_sid)
    return vr


@app.route("/")
def home():
  return "Hello, World!"


@app.get("/healthz")
def healthz():
    """Liveness and version probe.

    Deliberately unauthenticated: the container HEALTHCHECK and the deploy
    workflow both need to reach it without Twilio credentials. It exposes only
    the commit that is running — which is already public in the repo — and no
    call data or configuration.

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
    vr = render_step(STEPS["phase"], session)
    return str(vr), 200, {"Content-Type": "text/xml"}


@app.post("/gather/<step_id>")
@validate_twilio_request
def gather(step_id: str):
    call_sid = request.form.get("CallSid", "")
    session = get(call_sid)
    if session is None or step_id not in STEPS:
        # Session expired or unknown step — restart the tree cleanly.
        session = get_or_create(call_sid, request.form.get("From", ""))
        vr = render_step(STEPS["phase"], session)
        return str(vr), 200, {"Content-Type": "text/xml"}

    step = STEPS[step_id]
    raw_value = request.form.get("Digits") if step.input_type == "dtmf" else request.form.get("SpeechResult")

    if not raw_value:
        retries = session.retries.get(step_id, 0)
        if retries >= config.MAX_RETRIES_PER_STEP:
            session.answers[step.field] = step.skip_default
        else:
            session.retries[step_id] = retries + 1
            vr = render_step(step, session, prefix=step.retry_prompt + " ")
            return str(vr), 200, {"Content-Type": "text/xml"}
    elif step.input_type == "dtmf" and step.digit_map is not None:
        parsed = step.digit_map.get(raw_value)
        if parsed is None:
            retries = session.retries.get(step_id, 0)
            if retries >= config.MAX_RETRIES_PER_STEP:
                session.answers[step.field] = step.skip_default
            else:
                session.retries[step_id] = retries + 1
                vr = render_step(step, session, prefix=step.retry_prompt + " ")
                return str(vr), 200, {"Content-Type": "text/xml"}
        else:
            session.answers[step.field] = parsed
    else:
        session.answers[step.field] = raw_value.strip()

    next_id = step.next_id(session)
    if next_id == REPORT:
        vr = finish_call(session)
        return str(vr), 200, {"Content-Type": "text/xml"}

    vr = render_step(STEPS[next_id], session)
    return str(vr), 200, {"Content-Type": "text/xml"}


@app.post("/status")
@validate_twilio_request
def status():
    call_sid = request.form.get("CallSid", "")
    call_status = request.form.get("CallStatus", "")
    session = get(call_sid)
    if session is not None and not session.reported and call_status in (
        "completed", "busy", "no-answer", "failed", "canceled",
    ):
        try:
            subject = "[Abandoned call] " + report.build_subject(session)
            mailer.send_email(subject, report.build_report_text(session))
        except Exception:
            logger.exception("Failed to send abandoned-call report for call %s", call_sid)
        session.reported = True
        drop(call_sid)
    return "", 204


if __name__ == "__main__":
    app.run(port=5000, debug=True)
