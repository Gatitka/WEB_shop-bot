# Generated by Django 4.0 on 2024-06-10 13:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settings', '0002_alter_onlinesettings_close_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='onlinesettings',
            name='close_time',
            field=models.TimeField(blank=True, null=True, verbose_name='закрытие'),
        ),
        migrations.AlterField(
            model_name='onlinesettings',
            name='open_time',
            field=models.TimeField(blank=True, null=True, verbose_name='открытие'),
        ),
    ]
