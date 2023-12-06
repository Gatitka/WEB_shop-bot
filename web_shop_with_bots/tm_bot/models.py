from django.db import models
from django.contrib.auth.models import AbstractUser
# from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from django.conf import settings
# from users.models import BaseProfile


class TelegramAccount(models.Model):
    # создать метод очистки сохряняемых данных

    tm_id = models.CharField(
        'Telegram_ID',
        max_length=100,
        validators=[MinLengthValidator(4)],
        blank=True
    )
    tm_username = models.CharField(
        'Telegram_Username',
        max_length=100,
        validators=[MinLengthValidator(1)],
        blank=True, null=True
    )
    tm_subscription = models.BooleanField(
        'Telegram_subsription',
        default=True
    )
    tm_language = models.CharField(
        'Telegram_язык',
        max_length=3,
        choices=settings.LANGUAGE_CHOICES,
        default="RUS"
    )
    date_joined = models.DateTimeField(
        'Дата регистрации', auto_now_add=True
    )

    # дата последней активности

    notes = models.CharField(
        'Пометки',
        max_length=400,
        blank=True, null=True
    )

    class Meta:
        ordering = ['-date_joined']
        verbose_name = 'Telegram аккаунт'
        verbose_name_plural = 'Telegram аккаунты'

    def __str__(self):
        return f'Tm id = {self.tm_id}'


class Message(models.Model):
    profile = models.ForeignKey(
        to=TelegramAccount,
        verbose_name='Профиль',
        on_delete=models.PROTECT,
    )
    text = models.TextField(
        verbose_name='Текст',
    )
    created_at = models.DateTimeField(
        verbose_name='Время получения',
        auto_now_add=True,
    )

    def __str__(self) -> str:
        return f'Сообщение {self.pk} от {self.profile}'

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
