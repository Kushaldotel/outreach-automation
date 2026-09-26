from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('outreach', '0004_lead_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='city',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
