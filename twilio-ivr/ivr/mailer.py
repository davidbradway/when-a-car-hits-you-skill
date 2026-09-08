import logging
import smtplib
from email.message import EmailMessage

from . import config

logger = logging.getLogger(__name__)


def send_email(subject: str, body_text: str) -> None:
    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        # The report body carries the caller's phone number, crash location and
        # injury descriptions. Logging it unconditionally meant that a
        # misconfigured .env in production would quietly write every caller's
        # medical details into the container logs, where nobody is looking for
        # them and log shipping might carry them further. Opt in explicitly.
        if config.LOG_REPORT_BODY:
            logger.warning("SMTP not configured — report was:\n%s", body_text)
        else:
            logger.warning(
                "SMTP_USER/SMTP_PASSWORD not configured — skipping email send. "
                "Set LOG_REPORT_BODY=true to log the report body locally."
            )
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.REPORT_FROM_EMAIL
    msg["To"] = config.REPORT_TO_EMAIL
    msg.set_content(body_text)

    # smtplib defaults to NO timeout. This send runs inside the Twilio webhook
    # request, so an unresponsive SMTP host would hang the response until
    # gunicorn killed the worker — the caller would sit in silence and never
    # hear the closing guidance, and Twilio would log a webhook failure.
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=config.SMTP_TIMEOUT) as smtp:
        smtp.starttls()
        smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
        smtp.send_message(msg)
