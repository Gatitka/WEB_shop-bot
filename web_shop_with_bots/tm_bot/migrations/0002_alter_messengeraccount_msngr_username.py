# Generated by Django 4.0 on 2024-03-02 18:09

from django.db import migrations, models

import tm_bot.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tm_bot', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messengeraccount',
            name='msngr_username',
            field=models.CharField(blank=True, max_length=100, null=True, validators=[tm_bot.validators.validate_msngr_username], verbose_name='Username'),
        ),
    ]
