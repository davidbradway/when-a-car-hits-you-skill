import os

from dotenv import load_dotenv

load_dotenv()

TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
VALIDATE_TWILIO_SIGNATURE = os.environ.get("VALIDATE_TWILIO_SIGNATURE", "true").lower() == "true"

# Set at image build time (see Dockerfile) and reported by /healthz.
GIT_SHA = os.environ.get("GIT_SHA", "unknown")

# A Twilio Polly voice. See https://www.twilio.com/docs/voice/twiml/say/text-speech#polly-voices
VOICE = os.environ.get("TWILIO_VOICE", "Polly.Matthew")

MAX_RETRIES_PER_STEP = int(os.environ.get("MAX_RETRIES_PER_STEP", "2"))
