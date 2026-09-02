import logging
import smtplib
from email.message import EmailMessage

from . import config

logger = logging.getLogger(__name__)


def send_email(subject: str, body_text: str) -> None:
    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        logger.warning("SMTP_USER/SMTP_PASSWORD not configured — skipping email send. Report was:\n%s", body_text)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.REPORT_FROM_EMAIL
    msg["To"] = config.REPORT_TO_EMAIL
    msg.set_content(body_text)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
        smtp.send_message(msg)
