# Generated by Django 4.0 on 2024-03-30 12:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tm_bot', '0002_alter_messengeraccount_msngr_username'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messengeraccount',
            name='msngr_type',
            field=models.CharField(choices=[('tm', 'Telegram'), ('wts', 'WhatsApp'), ('vb', 'Viber')], max_length=3, verbose_name='msngr type'),
        ),
    ]
