"""IMAP fetch for reply detection. Adapted from the EICR backend imap.py."""

import email
import imaplib
import logging
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

TIMEOUT = 30


def _decode_header_value(value: str) -> str:
    parts = decode_header(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or 'utf-8', errors='replace'))
        else:
            result.append(part)
    return ''.join(result)


def _get_body_text(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain' and 'attachment' not in str(
                part.get('Content-Disposition', '')
            ):
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or 'utf-8', errors='replace')
        return ''
    payload = msg.get_payload(decode=True)
    if payload:
        return payload.decode(msg.get_content_charset() or 'utf-8', errors='replace')
    return ''


def fetch_new_messages(since_uid: str = '', since_days: int = None) -> list[dict]:
    """Fetch inbox messages. since_days forces a date-window search (re-poll);
    otherwise uses the UID cursor, falling back to a 7-day window on first run."""
    if not settings.GMAIL_EMAIL or not settings.GMAIL_APP_PASSWORD:
        raise RuntimeError('GMAIL_EMAIL / GMAIL_APP_PASSWORD not configured in backend/.env')

    conn = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT, timeout=TIMEOUT)
    try:
        conn.login(settings.GMAIL_EMAIL, settings.GMAIL_APP_PASSWORD)
        conn.select('INBOX')

        if since_days:
            since_date = (datetime.now() - timedelta(days=since_days)).strftime('%d-%b-%Y')
            status, data = conn.uid('search', None, f'SINCE {since_date}')
        elif since_uid:
            status, data = conn.uid('search', None, f'UID {int(since_uid) + 1}:*')
        else:
            since_date = (datetime.now() - timedelta(days=7)).strftime('%d-%b-%Y')
            status, data = conn.uid('search', None, f'SINCE {since_date}')

        if status != 'OK' or not data[0]:
            return []

        results = []
        for uid_bytes in data[0].split():
            uid = uid_bytes.decode()
            # Gmail returns the last UID again for "UID n+1:*" when nothing is new
            if not since_days and since_uid and int(uid) <= int(since_uid):
                continue

            status, msg_data = conn.uid('fetch', uid, '(RFC822)')
            if status != 'OK' or not msg_data or msg_data[0] is None:
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            sender_name, sender_email = parseaddr(msg.get('From', ''))
            try:
                received_at = parsedate_to_datetime(msg.get('Date', ''))
            except Exception:
                received_at = timezone.now()

            results.append({
                'uid': uid,
                'message_id': msg.get('Message-ID', '').strip(),
                'in_reply_to': msg.get('In-Reply-To', '').strip(),
                'references': msg.get('References', '').strip(),
                'sender_email': sender_email.lower(),
                'sender_name': _decode_header_value(sender_name) if sender_name else '',
                'subject': _decode_header_value(msg.get('Subject', '(no subject)')),
                'body_text': _get_body_text(msg),
                'received_at': received_at,
            })

        logger.info("IMAP fetched %d new message(s)", len(results))
        return results
    finally:
        try:
            conn.logout()
        except Exception:
            pass
