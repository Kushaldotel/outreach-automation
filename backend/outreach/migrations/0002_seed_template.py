from django.db import migrations

SUBJECT = "Quick question regarding {{company_name}}'s mobile bookings"

BODY = """Hey {{first_name}}, came across your page while looking at local service providers in your area.

I hit your website from my phone and noticed a couple of formatting bugs on the mobile layout that make it pretty difficult to quickly tap-to-call or request an emergency quote.

Our engineering team actually just wrapped up the new high-performance frameworks for Streamline Air (streamlineairfl.com) and Florida Doors (floridadoors.com) to solve this exact mobile drop-off issue.

We're looking to take on one more home service client in your region this month. I don't want to waste your time with a long pitch, but could I drop a quick 45-second loom video showing you the two main spots where your current site is bleeding mobile leads?

Let me know if you're open to seeing it."""


def seed_template(apps, schema_editor):
    EmailTemplate = apps.get_model('outreach', 'EmailTemplate')
    if not EmailTemplate.objects.exists():
        EmailTemplate.objects.create(subject=SUBJECT, body=BODY)


def unseed_template(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('outreach', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_template, unseed_template),
    ]
