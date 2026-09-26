from django.contrib import admin

from .models import AppState, DraftReply, EmailTemplate, InboxEmail, Lead, Reply, SentEmail


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'company_name', 'city', 'source', 'status', 'intent', 'sent_at']
    list_filter = ['source', 'status', 'intent']
    search_fields = ['email', 'first_name', 'last_name', 'company_name', 'city']


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ['lead', 'intent', 'subject', 'received_at']
    list_filter = ['intent']


@admin.register(DraftReply)
class DraftReplyAdmin(admin.ModelAdmin):
    list_display = ['lead', 'status', 'subject', 'created_at', 'sent_at']
    list_filter = ['status']


@admin.register(SentEmail)
class SentEmailAdmin(admin.ModelAdmin):
    list_display = ['to_email', 'lead', 'kind', 'subject', 'created_at']
    list_filter = ['kind']
    search_fields = ['to_email', 'subject']


@admin.register(InboxEmail)
class InboxEmailAdmin(admin.ModelAdmin):
    list_display = ['sender_email', 'sender_name', 'subject', 'category', 'is_lead', 'received_at']
    list_filter = ['is_lead']
    search_fields = ['sender_email', 'sender_name', 'subject']


admin.site.register(EmailTemplate)
admin.site.register(AppState)
