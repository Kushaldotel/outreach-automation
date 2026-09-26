from rest_framework import serializers

from .models import DraftReply, EmailTemplate, InboxEmail, Lead, Reply, SentEmail


class LeadSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Lead
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'title',
            'company_name', 'company_name_for_emails', 'city', 'email', 'email_status',
            'source', 'status', 'intent', 'sent_at', 'sent_subject', 'last_error', 'created_at',
        ]


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = ['id', 'subject', 'body', 'updated_at']


class ReplySerializer(serializers.ModelSerializer):
    lead_email = serializers.ReadOnlyField(source='lead.email')
    lead_name = serializers.ReadOnlyField(source='lead.full_name')
    company_name = serializers.ReadOnlyField(source='lead.company_name')

    class Meta:
        model = Reply
        fields = [
            'id', 'lead', 'lead_email', 'lead_name', 'company_name',
            'subject', 'body_text', 'intent', 'intent_reason', 'received_at', 'created_at',
        ]


class SentEmailSerializer(serializers.ModelSerializer):
    lead_name = serializers.ReadOnlyField(source='lead.full_name', default='')
    company_name = serializers.ReadOnlyField(source='lead.company_name', default='')
    lead_status = serializers.ReadOnlyField(source='lead.status', default='')
    lead_intent = serializers.ReadOnlyField(source='lead.intent', default='')

    class Meta:
        model = SentEmail
        fields = [
            'id', 'lead', 'lead_name', 'company_name', 'lead_status', 'lead_intent',
            'to_email', 'subject', 'body_text', 'kind', 'created_at',
        ]


class InboxEmailSerializer(serializers.ModelSerializer):
    category = serializers.ReadOnlyField()
    lead_name = serializers.ReadOnlyField(source='lead.full_name', default='')
    company_name = serializers.ReadOnlyField(source='lead.company_name', default='')
    intent = serializers.ReadOnlyField(source='reply.intent', default='')
    intent_reason = serializers.ReadOnlyField(source='reply.intent_reason', default='')
    replied_to_subject = serializers.ReadOnlyField(source='lead.sent_subject', default='')

    class Meta:
        model = InboxEmail
        fields = [
            'id', 'sender_email', 'sender_name', 'subject', 'body_text', 'received_at',
            'lead', 'lead_name', 'company_name', 'category', 'intent', 'intent_reason',
            'is_lead', 'classification_reason', 'replied_to_subject', 'created_at',
        ]


class DraftReplySerializer(serializers.ModelSerializer):
    lead_email = serializers.ReadOnlyField(source='lead.email')
    lead_name = serializers.ReadOnlyField(source='lead.full_name')
    company_name = serializers.ReadOnlyField(source='lead.company_name')
    lead_intent = serializers.ReadOnlyField(source='lead.intent')
    reply_body = serializers.ReadOnlyField(source='reply.body_text', default='')

    class Meta:
        model = DraftReply
        fields = [
            'id', 'lead', 'lead_email', 'lead_name', 'company_name', 'lead_intent',
            'reply', 'reply_body', 'subject', 'body_text', 'status',
            'sent_at', 'created_at',
        ]
        read_only_fields = ['status', 'sent_at']
