# Generated by Django 4.0 on 2024-07-13 00:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0005_auditlog_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditlog',
            name='ip',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='auditlog',
            name='ip_is_routable',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]