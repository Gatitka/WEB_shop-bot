# Generated by Django 4.0 on 2024-06-28 13:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_alter_baseprofile_messenger_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='baseprofile',
            name='first_web_order',
            field=models.BooleanField(default=False, verbose_name='Наличие заказов через сайт'),
        ),
    ]