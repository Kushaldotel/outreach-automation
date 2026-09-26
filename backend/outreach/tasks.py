import logging

from celery import shared_task
from django.core.cache import cache

from . import services

logger = logging.getLogger(__name__)

LOCK_KEY = 'poll_inbox_lock'
LOCK_TTL = 120  # seconds — expires even if a run crashes mid-poll


@shared_task
def send_campaign_task(lead_ids=None):
    """Send the campaign in the background so big lead lists don't block the API."""
    result = services.send_campaign(lead_ids=lead_ids)
    logger.info("send_campaign_task done: sent=%d failed=%d",
                len(result.get('sent', [])), len(result.get('failed', [])))
    return result


@shared_task
def poll_inbox_task():
    """Background inbox poll every 20s. Uses the IMAP UID cursor (our
    equivalent of Gmail's history id) so each run only fetches new mail.
    A cache lock skips the run if the previous one is still going."""
    if not cache.add(LOCK_KEY, '1', LOCK_TTL):
        logger.info("poll_inbox_task: previous run still in progress, skipping")
        return {'skipped': 'locked'}
    try:
        result = services.poll_inbox()
        if result['stored']:
            logger.info("poll_inbox_task: %s", result)
        return result
    except Exception as exc:
        logger.exception("poll_inbox_task failed")
        return {'error': str(exc)}
    finally:
        cache.delete(LOCK_KEY)
