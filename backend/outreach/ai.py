"""Claude calls: reply intent classification + soft-lead reply drafting."""

import json
import logging

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

MODEL = 'claude-haiku-4-5-20251001'


def _client() -> anthropic.Anthropic:
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError('ANTHROPIC_API_KEY not configured in backend/.env')
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        inner = lines[1:]
        if inner and inner[-1].strip() == '```':
            inner = inner[:-1]
        text = '\n'.join(inner).strip()
    return text


def _call(system: str, user_content: str) -> str:
    response = _client().messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{'role': 'user', 'content': user_content}],
    )
    logger.info(
        "[Claude] in=%d out=%d tokens",
        response.usage.input_tokens,
        response.usage.output_tokens,
    )
    return response.content[0].text


def classify_reply_intent(subject: str, body: str) -> dict:
    """Returns {"intent": soft_lead|main_lead|not_interested|other, "confidence": float, "reason": str}."""
    system = (
        "You classify replies to a cold outreach email from a web design agency. "
        "The original email offered to show the prospect a short video of mobile bugs on their website.\n\n"
        "Intent rules:\n"
        "- soft_lead: prospect asks for links, proof, examples, portfolio, more details, "
        "or says something like 'sure, send it over' / 'show me'.\n"
        "- main_lead: prospect asks to jump on a call, talk numbers, discuss pricing, "
        "or otherwise wants to talk business directly.\n"
        "- not_interested: clear rejection, unsubscribe request, 'not interested'.\n"
        "- other: auto-replies, out-of-office, bounces, unrelated messages, unclear.\n\n"
        'Respond ONLY with valid JSON: '
        '{"intent": "soft_lead|main_lead|not_interested|other", "confidence": 0.0-1.0, "reason": "..."}'
    )
    raw = _call(system, f"Subject: {subject}\n\n{body[:4000]}")
    result = json.loads(_strip_fences(raw))
    logger.info("[classify_reply_intent] intent=%s reason=%s", result.get('intent'), result.get('reason'))
    return result


def generate_main_lead_reply(lead, reply_body: str) -> str:
    """Draft a booking-link reply for a main lead (wants a call / to talk numbers)."""
    system = (
        "You write a short, warm, professional reply for a web design agency responding to a "
        "prospect who wants to jump on a call or talk pricing after a cold email about mobile "
        "bugs on their site. Requirements:\n"
        f"- Include this booking link naturally: {settings.CALENDLY_LINK}\n"
        "- Tone: 'Great — here's my booking link, grab any time that suits you.'\n"
        "- Friendly greeting using their first name, brief (under 100 words), no hard sell.\n"
        "- Sign off as 'Horizon Web Design team'.\n"
        "- Output ONLY the email body text, no subject line, no JSON."
    )
    user_content = (
        f"Prospect: {lead.full_name} ({lead.title}) at {lead.company_name}\n"
        f"Their reply:\n{reply_body[:2000]}"
    )
    return _call(system, user_content).strip()


def classify_inbound_email(sender: str, subject: str, body: str) -> dict:
    """Lead-or-not + intent for inbox emails from unknown senders.
    Returns {"is_lead": bool, "intent": "soft_lead"|"main_lead"|null,
             "confidence": float, "reason": str}."""
    system = (
        "You classify inbound emails for a web design agency's inbox. "
        "Determine if the email is a potential business lead — someone enquiring about "
        "web design, website services, website fixes, mobile optimization, or wanting to "
        "work with the agency — or not a lead (newsletter, spam, auto-reply, billing, "
        "supplier, job application, unrelated).\n\n"
        "If it IS a lead, also pick the intent:\n"
        "- soft_lead: general enquiry, asking about services, wants details, links, proof, "
        "examples, or exploring opportunities.\n"
        "- main_lead: wants to jump on a call, talk pricing/numbers, or buy now.\n"
        "If not a lead, intent is null.\n\n"
        'Respond ONLY with valid JSON: {"is_lead": true/false, "intent": "soft_lead"|"main_lead"|null, '
        '"confidence": 0.0-1.0, "reason": "..."}'
    )
    raw = _call(system, f"From: {sender}\nSubject: {subject}\n\n{body[:3000]}")
    result = json.loads(_strip_fences(raw))
    logger.info(
        "[classify_inbound_email] is_lead=%s intent=%s reason=%s",
        result.get('is_lead'), result.get('intent'), result.get('reason'),
    )
    return result


def generate_soft_lead_reply(lead, reply_body: str) -> str:
    """Draft a respectful reply body dropping the portfolio link."""
    system = (
        "You write a short, warm, professional reply for a web design agency responding to a "
        "prospect who asked for proof/links/details after a cold email about mobile bugs on their site. "
        "Requirements:\n"
        f"- Include this portfolio link naturally: {settings.PORTFOLIO_LINK}\n"
        "- Respectful, brief (under 120 words), no hard sell.\n"
        "- Mention you can still send the short video walkthrough of their site's mobile issues.\n"
        "- Sign off as 'Horizon Web Design team'.\n"
        "- Output ONLY the email body text, no subject line, no JSON."
    )
    user_content = (
        f"Prospect: {lead.full_name} ({lead.title}) at {lead.company_name}\n"
        f"Their reply:\n{reply_body[:2000]}"
    )
    return _call(system, user_content).strip()
