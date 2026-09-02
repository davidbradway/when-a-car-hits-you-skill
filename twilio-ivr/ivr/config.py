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
