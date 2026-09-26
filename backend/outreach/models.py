from django.db import models


class Lead(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        REPLIED = 'replied', 'Replied'
        FAILED = 'failed', 'Send Failed'

    class Intent(models.TextChoices):
        NONE = 'none', 'None'
        SOFT_LEAD = 'soft_lead', 'Soft Lead'
        MAIN_LEAD = 'main_lead', 'Main Lead'
        NOT_INTERESTED = 'not_interested', 'Not Interested'
        OTHER = 'other', 'Other'

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=255, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    company_name_for_emails = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(unique=True)
    email_status = models.CharField(max_length=50, blank=True)

    class Source(models.TextChoices):
        CUSTOM = 'custom', 'Custom'      # uploaded CSV / added manually
        INBOX = 'inbox', 'Inbox'         # discovered from incoming email

    source = models.CharField(max_length=20, choices=Source.choices, default=Source.CUSTOM)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    intent = models.CharField(max_length=20, choices=Intent.choices, default=Intent.NONE)

    sent_at = models.DateTimeField(null=True, blank=True)
    sent_message_id = models.CharField(max_length=255, blank=True)
    sent_subject = models.CharField(max_length=500, blank=True)
    last_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.full_name} <{self.email}>"


class EmailTemplate(models.Model):
    """Singleton campaign template. Placeholders: {{first_name}}, {{company_name}}."""

    subject = models.CharField(max_length=500)
    body = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject

    @classmethod
    def get_solo(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create(subject='', body='')
        return obj


class Reply(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='replies')
    message_id = models.CharField(max_length=255, unique=True)
    in_reply_to = models.CharField(max_length=255, blank=True)
    references = models.TextField(blank=True)
    subject = models.CharField(max_length=500, blank=True)
    body_text = models.TextField(blank=True)
    intent = models.CharField(
        max_length=20, choices=Lead.Intent.choices, default=Lead.Intent.OTHER
    )
    intent_reason = models.CharField(max_length=500, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'replies'

    def __str__(self):
        return f"Reply from {self.lead.email} ({self.intent})"


class DraftReply(models.Model):
    """AI-drafted reply to a soft lead, awaiting human approval."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Approval'
        SENT = 'sent', 'Sent'
        REJECTED = 'rejected', 'Rejected'
        FAILED = 'failed', 'Send Failed'

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='drafts')
    reply = models.ForeignKey(
        Reply, null=True, blank=True, on_delete=models.SET_NULL, related_name='drafts'
    )
    subject = models.CharField(max_length=500)
    body_text = models.TextField()
    in_reply_to = models.CharField(max_length=255, blank=True)
    references = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'draft replies'

    def __str__(self):
        return f"Draft to {self.lead.email} ({self.status})"


class AppState(models.Model):
    """Singleton for IMAP polling cursor + settings."""

    last_uid = models.CharField(max_length=50, blank=True)
    poll_days = models.PositiveIntegerField(default=7)

    @classmethod
    def get_solo(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj


class SentEmail(models.Model):
    """Log of every outbound email (campaign sends + approved draft replies)."""

    class Kind(models.TextChoices):
        CAMPAIGN = 'campaign', 'Campaign'
        REPLY = 'reply', 'Draft Reply'

    lead = models.ForeignKey(
        Lead, null=True, blank=True, on_delete=models.SET_NULL, related_name='sent_emails'
    )
    to_email = models.EmailField()
    subject = models.CharField(max_length=500)
    body_text = models.TextField()
    message_id = models.CharField(max_length=255, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.CAMPAIGN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.kind} -> {self.to_email}"


class InboxEmail(models.Model):
    """Every polled inbox message. Lead replies link to their Reply record;
    unknown senders get a lead-or-not classification."""

    uid = models.CharField(max_length=50, blank=True)
    message_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    sender_email = models.EmailField()
    sender_name = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=500, blank=True)
    body_text = models.TextField(blank=True)
    received_at = models.DateTimeField(null=True, blank=True)

    lead = models.ForeignKey(
        Lead, null=True, blank=True, on_delete=models.SET_NULL, related_name='inbox_emails'
    )
    reply = models.OneToOneField(
        Reply, null=True, blank=True, on_delete=models.SET_NULL, related_name='inbox_email'
    )
    is_lead = models.BooleanField(null=True)  # unknown senders: Claude lead-or-not verdict
    classification_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_at', '-created_at']

    @property
    def category(self) -> str:
        if self.is_lead:
            return 'new_lead'   # enquiry from an unknown sender, promoted to inbox lead
        if self.reply_id:
            return 'reply'      # reply from one of our campaign leads
        return 'other'

    def __str__(self):
        return f"{self.sender_email}: {self.subject[:50]}"
