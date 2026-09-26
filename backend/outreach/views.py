import logging

from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from . import services
from .models import AppState, DraftReply, EmailTemplate, InboxEmail, Lead, Reply, SentEmail
from .serializers import (
    DraftReplySerializer,
    EmailTemplateSerializer,
    InboxEmailSerializer,
    LeadSerializer,
    ReplySerializer,
    SentEmailSerializer,
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@parser_classes([MultiPartParser])
def upload_leads(request):
    file_obj = request.FILES.get('file')
    if file_obj is None:
        return Response({'error': "Attach a CSV as form field 'file'."}, status=400)
    result = services.import_leads_csv(file_obj)
    return Response(result, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
def list_leads(request):
    if request.method == 'POST':
        serializer = LeadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    leads = Lead.objects.all()
    if request.GET.get('status'):
        leads = leads.filter(status=request.GET['status'])
    if request.GET.get('intent'):
        leads = leads.filter(intent=request.GET['intent'])
    return Response(LeadSerializer(leads, many=True).data)


@api_view(['POST'])
def bulk_delete_leads(request):
    if request.data.get('all'):
        qs = Lead.objects.all()
    else:
        ids = request.data.get('lead_ids') or []
        if not ids:
            return Response({'error': "Pass lead_ids list or all: true."}, status=400)
        qs = Lead.objects.filter(id__in=ids)
    count = qs.count()
    qs.delete()
    return Response({'deleted': count})


@api_view(['GET', 'PATCH', 'DELETE'])
def lead_detail(request, pk):
    try:
        lead = Lead.objects.get(pk=pk)
    except Lead.DoesNotExist:
        return Response({'error': 'Lead not found.'}, status=404)

    if request.method == 'DELETE':
        lead.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == 'PATCH':
        serializer = LeadSerializer(lead, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    return Response(LeadSerializer(lead).data)


@api_view(['GET', 'PUT'])
def template_view(request):
    template = EmailTemplate.get_solo()
    if request.method == 'PUT':
        serializer = EmailTemplateSerializer(template, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    return Response(EmailTemplateSerializer(template).data)


@api_view(['POST'])
def send_campaign(request):
    lead_ids = request.data.get('lead_ids')

    template = EmailTemplate.get_solo()
    if not template.subject or not template.body:
        return Response({'error': 'Email template is empty — set subject and body first.'}, status=400)

    if lead_ids:
        eligible = Lead.objects.filter(id__in=lead_ids)
    else:
        eligible = Lead.objects.filter(status__in=[Lead.Status.PENDING, Lead.Status.FAILED])
    count = eligible.count()
    if count == 0:
        return Response({'error': 'No leads in selection.'}, status=400)

    from .tasks import send_campaign_task
    try:
        send_campaign_task.delay(lead_ids)
        return Response({'queued': count})
    except Exception:
        logger.warning("Celery unavailable — sending synchronously")
        result = services.send_campaign(lead_ids=lead_ids)
        if 'error' in result:
            return Response(result, status=400)
        return Response(result)


@api_view(['POST'])
def poll_inbox(request):
    days = request.data.get('days')
    try:
        days = int(days) if days else None
    except (TypeError, ValueError):
        return Response({'error': 'days must be a number.'}, status=400)
    try:
        result = services.poll_inbox(days=days)
    except Exception as exc:
        logger.exception("poll_inbox failed")
        return Response({'error': str(exc)}, status=502)
    return Response(result)


@api_view(['GET'])
def list_inbox(request):
    emails = InboxEmail.objects.select_related('lead', 'reply').all()
    category = request.GET.get('category')
    if category == 'reply':
        emails = emails.filter(reply__isnull=False)
    elif category == 'new_lead':
        emails = emails.filter(is_lead=True)
    elif category == 'other':
        emails = emails.filter(reply__isnull=True).exclude(is_lead=True)
    return Response(InboxEmailSerializer(emails[:200], many=True).data)


@api_view(['POST'])
def reanalyze_inbox(request, pk):
    try:
        inbox_email = InboxEmail.objects.select_related('lead', 'reply').get(pk=pk)
    except InboxEmail.DoesNotExist:
        return Response({'error': 'Inbox email not found.'}, status=404)
    try:
        inbox_email = services.reanalyze_inbox_email(inbox_email)
    except Exception as exc:
        logger.exception("reanalyze failed")
        return Response({'error': str(exc)}, status=502)
    return Response(InboxEmailSerializer(inbox_email).data)


@api_view(['GET'])
def list_sent(request):
    emails = SentEmail.objects.select_related('lead').all()
    if request.GET.get('kind'):
        emails = emails.filter(kind=request.GET['kind'])
    return Response(SentEmailSerializer(emails[:200], many=True).data)


@api_view(['GET', 'PUT'])
def app_settings(request):
    state = AppState.get_solo()
    if request.method == 'PUT':
        days = request.data.get('poll_days')
        try:
            state.poll_days = max(1, int(days))
        except (TypeError, ValueError):
            return Response({'error': 'poll_days must be a positive number.'}, status=400)
        state.save()
    return Response({'poll_days': state.poll_days, 'last_uid': state.last_uid})


@api_view(['GET'])
def list_replies(request):
    replies = Reply.objects.select_related('lead').all()
    if request.GET.get('intent'):
        replies = replies.filter(intent=request.GET['intent'])
    return Response(ReplySerializer(replies, many=True).data)


@api_view(['GET'])
def list_drafts(request):
    drafts = DraftReply.objects.select_related('lead', 'reply').all()
    if request.GET.get('status'):
        drafts = drafts.filter(status=request.GET['status'])
    return Response(DraftReplySerializer(drafts, many=True).data)


@api_view(['PATCH'])
def update_draft(request, pk):
    try:
        draft = DraftReply.objects.get(pk=pk)
    except DraftReply.DoesNotExist:
        return Response({'error': 'Draft not found.'}, status=404)
    serializer = DraftReplySerializer(draft, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(['POST'])
def send_draft(request, pk):
    try:
        draft = DraftReply.objects.select_related('lead').get(pk=pk)
    except DraftReply.DoesNotExist:
        return Response({'error': 'Draft not found.'}, status=404)
    if draft.status == DraftReply.Status.SENT:
        return Response({'error': 'Draft already sent.'}, status=400)
    try:
        services.send_draft(draft)
    except Exception as exc:
        logger.exception("Draft send failed")
        draft.status = DraftReply.Status.FAILED
        draft.save()
        return Response({'error': str(exc)}, status=502)
    return Response(DraftReplySerializer(draft).data)


@api_view(['POST'])
def reject_draft(request, pk):
    try:
        draft = DraftReply.objects.get(pk=pk)
    except DraftReply.DoesNotExist:
        return Response({'error': 'Draft not found.'}, status=404)
    draft.status = DraftReply.Status.REJECTED
    draft.save()
    return Response(DraftReplySerializer(draft).data)


@api_view(['GET'])
def stats(request):
    return Response({
        'leads_total': Lead.objects.count(),
        'leads_pending': Lead.objects.filter(status=Lead.Status.PENDING).count(),
        'leads_sent': Lead.objects.filter(status=Lead.Status.SENT).count(),
        'leads_replied': Lead.objects.filter(status=Lead.Status.REPLIED).count(),
        'leads_failed': Lead.objects.filter(status=Lead.Status.FAILED).count(),
        'soft_leads': Lead.objects.filter(intent=Lead.Intent.SOFT_LEAD).count(),
        'main_leads': Lead.objects.filter(intent=Lead.Intent.MAIN_LEAD).count(),
        'drafts_pending': DraftReply.objects.filter(status=DraftReply.Status.PENDING).count(),
        'emails_sent': SentEmail.objects.count(),
        'inbox_total': InboxEmail.objects.count(),
        'inbox_new_leads': InboxEmail.objects.filter(is_lead=True).count(),
    })
