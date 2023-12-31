# Generated by Django 4.0 on 2023-11-27 00:24

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TelegramAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tm_id', models.CharField(blank=True, max_length=100, validators=[django.core.validators.MinLengthValidator(4)], verbose_name='Telegram_ID')),
                ('tm_username', models.CharField(blank=True, max_length=100, null=True, validators=[django.core.validators.MinLengthValidator(1)], verbose_name='Telegram_Username')),
                ('tm_subscription', models.BooleanField(default=True, verbose_name='Telegram_subsription')),
                ('tm_language', models.CharField(choices=[('EN', 'English'), ('RUS', 'Русский'), ('SRB', 'Српски')], default='RUS', max_length=3, verbose_name='Telegram_язык')),
                ('add_date', models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')),
                ('notes', models.CharField(blank=True, max_length=400, null=True, verbose_name='Пометки')),
            ],
            options={
                'verbose_name': 'Telegram аккаунт',
                'verbose_name_plural': 'Telegram аккаунты',
                'ordering': ['-add_date'],
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(verbose_name='Текст')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Время получения')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tm_bot.telegramaccount', verbose_name='Профиль')),
            ],
            options={
                'verbose_name': 'Сообщение',
                'verbose_name_plural': 'Сообщения',
            },
        ),
    ]
