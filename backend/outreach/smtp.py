import logging
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings

logger = logging.getLogger(__name__)


class SMTPError(Exception):
    pass


def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    in_reply_to: str = '',
    references: str = '',
) -> str:
    """Send a plain-text email via Gmail SMTP. Returns the generated Message-ID."""
    if not settings.GMAIL_EMAIL or not settings.GMAIL_APP_PASSWORD:
        raise SMTPError('GMAIL_EMAIL / GMAIL_APP_PASSWORD not configured in backend/.env')

    from_address = settings.GMAIL_EMAIL
    domain = from_address.split('@')[-1]
    message_id = f"<{uuid.uuid4().hex}@{domain}>"

    msg = MIMEMultipart('alternative')
    msg['Message-ID'] = message_id

    if in_reply_to:
        msg['In-Reply-To'] = in_reply_to
        if references:
            msg['References'] = references
        if subject and not subject.lower().startswith('re:'):
            subject = f"Re: {subject}"

    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = to_email
    msg['Reply-To'] = from_address
    msg.attach(MIMEText(body_text, 'plain', 'utf-8'))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.login(from_address, settings.GMAIL_APP_PASSWORD)
        server.sendmail(from_address, [to_email], msg.as_string())

    logger.info("Sent email to %s (%s)", to_email, message_id)
    return message_id
