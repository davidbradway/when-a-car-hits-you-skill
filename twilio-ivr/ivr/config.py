import os

from dotenv import load_dotenv

load_dotenv()

TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
VALIDATE_TWILIO_SIGNATURE = os.environ.get("VALIDATE_TWILIO_SIGNATURE", "true").lower() == "true"

REPORT_TO_EMAIL = os.environ.get("REPORT_TO_EMAIL", "david.bradway@gmail.com")
REPORT_FROM_EMAIL = os.environ.get("REPORT_FROM_EMAIL", REPORT_TO_EMAIL)

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

# Seconds. The report is emailed from inside the Twilio webhook request, and
# Twilio abandons a webhook after roughly 15 seconds — so this must stay
# comfortably below that or the caller never hears the closing guidance.
SMTP_TIMEOUT = float(os.environ.get("SMTP_TIMEOUT", "10"))

# The crash report contains the caller's phone number, crash location and
# injury descriptions. When SMTP is unconfigured the report is only written to
# the log if this is explicitly enabled — useful locally, never in production.
LOG_REPORT_BODY = os.environ.get("LOG_REPORT_BODY", "false").lower() == "true"

# Set at image build time (see Dockerfile) and reported by /healthz.
GIT_SHA = os.environ.get("GIT_SHA", "unknown")

# A Twilio Polly voice. See https://www.twilio.com/docs/voice/twiml/say/text-speech#polly-voices
VOICE = os.environ.get("TWILIO_VOICE", "Polly.Matthew")

MAX_RETRIES_PER_STEP = int(os.environ.get("MAX_RETRIES_PER_STEP", "2"))

CONTRIBUTORY_NEGLIGENCE_STATES = {
    "nc", "north carolina",
    "va", "virginia",
    "md", "maryland",
    "al", "alabama",
    "dc", "washington dc", "washington d.c.", "district of columbia",
}
