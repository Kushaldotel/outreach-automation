"""Core flows: CSV import, campaign send, reply processing."""

import csv
import io
import logging
import re
import time

from django.conf import settings
from django.utils import timezone

from . import ai, imap, smtp
from .models import AppState, DraftReply, EmailTemplate, InboxEmail, Lead, Reply, SentEmail

logger = logging.getLogger(__name__)

# CSV header -> Lead field
CSV_FIELD_MAP = {
    'first name': 'first_name',
    'last name': 'last_name',
    'title': 'title',
    'company name': 'company_name',
    'company name for emails': 'company_name_for_emails',
    'city': 'city',
    'email': 'email',
    'email status': 'email_status',
}


def import_leads_csv(file_obj) -> dict:
    """Import/update leads from an uploaded CSV (comma or tab delimited)."""
    raw = file_obj.read()
    text = raw.decode('utf-8-sig', errors='replace')

    try:
        dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=',\t;')
    except (csv.Error, IndexError):
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    created, updated, skipped = 0, 0, 0

    for row in reader:
        data = {}
        for key, value in row.items():
            if key is None:
                continue
            field = CSV_FIELD_MAP.get(key.strip().lower())
            if field and value:
                data[field] = value.strip()

        email_addr = data.pop('email', '').lower()
        if not email_addr or '@' not in email_addr:
            skipped += 1
            continue

        _, was_created = Lead.objects.update_or_create(email=email_addr, defaults=data)
        if was_created:
            created += 1
        else:
            updated += 1

    logger.info("CSV import: %d created, %d updated, %d skipped", created, updated, skipped)
    return {'created': created, 'updated': updated, 'skipped': skipped}


def render_template(text: str, lead: Lead) -> str:
    """Replace {{first_name}} / {first_name} style placeholders."""
    values = {
        'first_name': lead.first_name,
        'last_name': lead.last_name,
        'full_name': lead.full_name,
        'company_name': lead.company_name_for_emails or lead.company_name,
        'title': lead.title,
        'city': lead.city or '',
    }

    def sub(match):
        key = match.group(1).strip().lower()
        return values.get(key, match.group(0))

    return re.sub(r'\{\{?\s*(\w+)\s*\}?\}', sub, text)


def send_campaign(lead_ids: list[int] | None = None) -> dict:
    """Send the campaign template to pending leads, one by one."""
    template = EmailTemplate.get_solo()
    if not template.subject or not template.body:
        return {'error': 'Email template is empty — set subject and body first.'}

    # Explicit selection sends to exactly those leads, whatever their status
    # (re-sends, follow-ups to soft/main leads). Without a selection, only
    # pending/failed leads get the campaign.
    if lead_ids:
        leads = Lead.objects.filter(id__in=lead_ids)
    else:
        leads = Lead.objects.filter(status__in=[Lead.Status.PENDING, Lead.Status.FAILED])

    sent, failed = [], []
    leads = list(leads)
    for i, lead in enumerate(leads):
        subject = render_template(template.subject, lead)
        body = render_template(template.body, lead)
        try:
            message_id = smtp.send_email(lead.email, subject, body)
            lead.status = Lead.Status.SENT
            lead.sent_at = timezone.now()
            lead.sent_message_id = message_id
            lead.sent_subject = subject
            lead.last_error = ''
            SentEmail.objects.create(
                lead=lead,
                to_email=lead.email,
                subject=subject,
                body_text=body,
                message_id=message_id,
                kind=SentEmail.Kind.CAMPAIGN,
            )
            sent.append(lead.email)
        except Exception as exc:
            logger.exception("Send failed for %s", lead.email)
            lead.status = Lead.Status.FAILED
            lead.last_error = str(exc)
            failed.append({'email': lead.email, 'error': str(exc)})
        lead.save()

        if i < len(leads) - 1:
            time.sleep(settings.SEND_DELAY_SECONDS)

    return {'sent': sent, 'failed': failed, 'total': len(leads)}


def _process_lead_reply(lead: Lead, m: dict) -> Reply:
    """Existing lead replied: classify intent, maybe draft a soft-lead response."""
    try:
        result = ai.classify_reply_intent(m['subject'], m['body_text'])
        intent = result.get('intent', 'other')
        reason = result.get('reason', '')
    except Exception as exc:
        logger.exception("Intent classification failed for %s", m['sender_email'])
        intent, reason = Lead.Intent.OTHER, f'classification failed: {exc}'

    if intent not in Lead.Intent.values:
        intent = Lead.Intent.OTHER

    reply = Reply.objects.create(
        lead=lead,
        message_id=m['message_id'],
        in_reply_to=m['in_reply_to'],
        references=m['references'],
        subject=m['subject'],
        body_text=m['body_text'],
        intent=intent,
        intent_reason=reason,
        received_at=m['received_at'],
    )

    lead.status = Lead.Status.REPLIED
    lead.intent = intent
    lead.save()

    _create_intent_draft(lead, reply, m, intent)
    return reply


def _create_intent_draft(lead: Lead, reply: Reply, m: dict, intent: str):
    """Intent logic rules: soft lead -> portfolio-link draft; main lead -> booking-link
    draft. Both wait for approval. Everything else is ignored (no draft)."""
    if intent not in (Lead.Intent.SOFT_LEAD, Lead.Intent.MAIN_LEAD):
        return
    # Never draft twice for the same incoming message (covers re-analysis after
    # a draft was already created or sent), and one pending draft per lead max.
    if reply is not None and DraftReply.objects.filter(reply=reply).exists():
        logger.info("[inbox] draft already exists for this message — skipping draft")
        return
    if DraftReply.objects.filter(lead=lead, status=DraftReply.Status.PENDING).exists():
        return

    try:
        if intent == Lead.Intent.MAIN_LEAD:
            body = ai.generate_main_lead_reply(lead, m['body_text'])
        else:
            body = ai.generate_soft_lead_reply(lead, m['body_text'])
    except Exception:
        logger.exception("Draft generation failed for %s", lead.email)
        if intent == Lead.Intent.MAIN_LEAD:
            body = (
                f"Hey {lead.first_name},\n\nGreat to hear from you! "
                f"Here's my booking link — grab any time that works for you:\n"
                f"{settings.CALENDLY_LINK}\n\nLooking forward to talking.\n\n"
                "Horizon Web Design team"
            )
        else:
            body = (
                f"Hey {lead.first_name},\n\nThanks for reaching out! "
                f"Here's our portfolio: {settings.PORTFOLIO_LINK}\n\n"
                "Happy to share more details about our services whenever suits.\n\n"
                "Horizon Web Design team"
            )
    references = (m['references'] + ' ' + m['message_id']).strip()
    DraftReply.objects.create(
        lead=lead,
        reply=reply,
        subject=m['subject'] or lead.sent_subject,
        body_text=body,
        in_reply_to=m['message_id'],
        references=references,
    )
    logger.info(
        "[inbox] DRAFT CREATED for %s (%s) — waiting for approval",
        lead.email,
        'booking link' if intent == Lead.Intent.MAIN_LEAD else 'portfolio link',
    )


def _create_inbox_lead(m: dict, intent: str, reason: str) -> tuple[Lead, Reply]:
    """Unknown sender with lead intent: create an inbox-source Lead + Reply + draft."""
    sender_name = (m['sender_name'] or '').strip()
    if sender_name:
        parts = sender_name.split(None, 1)
        first_name, last_name = parts[0], parts[1] if len(parts) > 1 else ''
    else:
        first_name, last_name = m['sender_email'].split('@')[0], ''

    lead = Lead.objects.create(
        first_name=first_name,
        last_name=last_name,
        email=m['sender_email'],
        source=Lead.Source.INBOX,
        status=Lead.Status.REPLIED,
        intent=intent,
    )
    reply = Reply.objects.create(
        lead=lead,
        message_id=m['message_id'],
        in_reply_to=m['in_reply_to'],
        references=m['references'],
        subject=m['subject'],
        body_text=m['body_text'],
        intent=intent,
        intent_reason=reason,
        received_at=m['received_at'],
    )
    logger.info(
        "[inbox] INBOX LEAD CREATED: %s (%s) — %s",
        lead.email, intent.upper(), reason[:120],
    )
    _create_intent_draft(lead, reply, m, intent)
    return lead, reply


def poll_inbox(days: int = None) -> dict:
    """Poll Gmail inbox and store every message.

    - Lead replies -> intent classification + soft-lead draft (existing flow).
    - Unknown senders -> Claude lead-or-not classification.
    Pass days to force a re-poll of the last N days instead of the UID cursor.
    """
    state = AppState.get_solo()

    if days:
        messages = imap.fetch_new_messages(since_days=days)
    elif state.last_uid:
        messages = imap.fetch_new_messages(since_uid=state.last_uid)
    else:
        messages = imap.fetch_new_messages(since_days=state.poll_days)

    own_email = (settings.GMAIL_EMAIL or '').lower()
    stored, skipped = 0, 0
    replies, new_leads = [], []
    max_uid = int(state.last_uid) if state.last_uid else 0

    for m in messages:
        try:
            max_uid = max(max_uid, int(m['uid']))
        except (TypeError, ValueError):
            pass

        if m['sender_email'] == own_email:
            skipped += 1
            continue

        message_id = m['message_id'] or None
        if message_id and InboxEmail.objects.filter(message_id=message_id).exists():
            skipped += 1
            continue

        inbox_email = InboxEmail(
            uid=m['uid'],
            message_id=message_id,
            sender_email=m['sender_email'],
            sender_name=m['sender_name'],
            subject=m['subject'],
            body_text=m['body_text'],
            received_at=m['received_at'],
        )

        logger.info(
            "[inbox] NEW EMAIL from %s <%s> — subject: %r",
            m['sender_name'] or '?', m['sender_email'], m['subject'][:100],
        )

        lead = Lead.objects.filter(email__iexact=m['sender_email']).first()
        if lead is not None:
            inbox_email.lead = lead
            if message_id and not Reply.objects.filter(message_id=message_id).exists():
                logger.info("[inbox] sender matches lead %s — classifying reply intent...", lead.email)
                reply = _process_lead_reply(lead, m)
                inbox_email.reply = reply
                replies.append({'email': lead.email, 'intent': reply.intent})
                logger.info(
                    "[inbox] VERDICT: %s -> %s (%s)",
                    lead.email, reply.intent.upper(), reply.intent_reason[:150],
                )
            else:
                logger.info("[inbox] lead %s message already processed, stored only", lead.email)
        else:
            logger.info("[inbox] unknown sender — running lead-or-not classification...")
            try:
                result = ai.classify_inbound_email(
                    m['sender_email'], m['subject'], m['body_text']
                )
                inbox_email.is_lead = bool(result.get('is_lead'))
                inbox_email.classification_reason = result.get('reason', '')[:500]
            except Exception as exc:
                logger.exception("Inbound classification failed for %s", m['sender_email'])
                result = {}
                inbox_email.classification_reason = f'classification failed: {exc}'[:500]

            if inbox_email.is_lead:
                intent = result.get('intent')
                if intent not in (Lead.Intent.SOFT_LEAD, Lead.Intent.MAIN_LEAD):
                    intent = Lead.Intent.SOFT_LEAD
                if message_id:
                    lead, reply = _create_inbox_lead(
                        m, intent, inbox_email.classification_reason
                    )
                    inbox_email.lead = lead
                    inbox_email.reply = reply
                new_leads.append(m['sender_email'])

            logger.info(
                "[inbox] VERDICT: %s -> %s (%s)",
                m['sender_email'],
                'NEW LEAD' if inbox_email.is_lead else 'NOT A LEAD',
                inbox_email.classification_reason[:150],
            )

        inbox_email.save()
        stored += 1

    if max_uid:
        state.last_uid = str(max_uid)
        state.save()

    return {
        'fetched': len(messages),
        'stored': stored,
        'skipped': skipped,
        'lead_replies': replies,
        'new_leads': new_leads,
    }


def reanalyze_inbox_email(inbox_email: InboxEmail) -> InboxEmail:
    """Re-run AI classification on a stored inbox email.

    Safe to repeat: never creates a second draft for the same message
    (drafted or already sent), and never duplicates leads/replies.
    Useful when an email was misclassified or a previous analysis failed.
    """
    m = {
        'sender_name': inbox_email.sender_name,
        'sender_email': inbox_email.sender_email,
        'message_id': inbox_email.message_id or '',
        'in_reply_to': inbox_email.reply.in_reply_to if inbox_email.reply else '',
        'references': inbox_email.reply.references if inbox_email.reply else '',
        'subject': inbox_email.subject,
        'body_text': inbox_email.body_text,
        'received_at': inbox_email.received_at,
    }

    lead = inbox_email.lead or Lead.objects.filter(
        email__iexact=inbox_email.sender_email
    ).first()

    if lead is not None:
        result = ai.classify_reply_intent(m['subject'], m['body_text'])
        intent = result.get('intent', 'other')
        if intent not in Lead.Intent.values:
            intent = Lead.Intent.OTHER
        reason = result.get('reason', '')

        reply = inbox_email.reply
        if reply is None and m['message_id']:
            reply = Reply.objects.filter(message_id=m['message_id']).first()
        if reply is not None:
            reply.intent = intent
            reply.intent_reason = reason
            reply.save()
        elif m['message_id']:
            reply = Reply.objects.create(
                lead=lead,
                message_id=m['message_id'],
                in_reply_to=m['in_reply_to'],
                references=m['references'],
                subject=m['subject'],
                body_text=m['body_text'],
                intent=intent,
                intent_reason=reason,
                received_at=m['received_at'],
            )

        lead.intent = intent
        lead.status = Lead.Status.REPLIED
        lead.save()

        inbox_email.lead = lead
        inbox_email.reply = reply
        if lead.source == Lead.Source.INBOX:
            inbox_email.is_lead = intent in (Lead.Intent.SOFT_LEAD, Lead.Intent.MAIN_LEAD)
        inbox_email.classification_reason = reason[:500]
        logger.info(
            "[reanalyze] %s -> %s (%s)", lead.email, intent.upper(), reason[:120]
        )
        _create_intent_draft(lead, reply, m, intent)
    else:
        result = ai.classify_inbound_email(m['sender_email'], m['subject'], m['body_text'])
        inbox_email.is_lead = bool(result.get('is_lead'))
        inbox_email.classification_reason = result.get('reason', '')[:500]
        logger.info(
            "[reanalyze] %s -> %s (%s)",
            m['sender_email'],
            'NEW LEAD' if inbox_email.is_lead else 'NOT A LEAD',
            inbox_email.classification_reason[:150],
        )
        if inbox_email.is_lead and m['message_id']:
            intent = result.get('intent')
            if intent not in (Lead.Intent.SOFT_LEAD, Lead.Intent.MAIN_LEAD):
                intent = Lead.Intent.SOFT_LEAD
            new_lead, reply = _create_inbox_lead(
                m, intent, inbox_email.classification_reason
            )
            inbox_email.lead = new_lead
            inbox_email.reply = reply

    inbox_email.save()
    return inbox_email


def send_draft(draft: DraftReply) -> DraftReply:
    message_id = smtp.send_email(
        draft.lead.email,
        draft.subject,
        draft.body_text,
        in_reply_to=draft.in_reply_to,
        references=draft.references,
    )
    draft.status = DraftReply.Status.SENT
    draft.sent_at = timezone.now()
    draft.save()
    SentEmail.objects.create(
        lead=draft.lead,
        to_email=draft.lead.email,
        subject=draft.subject,
        body_text=draft.body_text,
        message_id=message_id,
        kind=SentEmail.Kind.REPLY,
    )
    logger.info("Draft %s sent to %s (%s)", draft.pk, draft.lead.email, message_id)
    return draft
