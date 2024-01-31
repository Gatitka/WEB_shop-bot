from django.conf import settings
from django.contrib.auth.models import AbstractUser
# from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

# from users.models import BaseProfile

MESSENGERS = [
    ('tm', 'Telegram'),
    ('wts', 'WhatsApp'),
    ('vb', 'Viber'),
]


class MessengerAccount(models.Model):
    # создать метод очистки сохряняемых данных
    msngr_type = models.CharField(
        'Тип мессенджера',
        max_length=3,  # Устанавливаем максимальную длину, соответствующую максимальной длине кодов мессенджеров
        choices=MESSENGERS,
    )
    msngr_id = models.CharField(
        'ID',
        max_length=100,
        validators=[MinLengthValidator(4)],
        blank=True, null=True
    )
    msngr_username = models.CharField(
        'Username',
        max_length=100,
        validators=[MinLengthValidator(1)],
        blank=True, null=True
    )
    msngr_phone = PhoneNumberField(
        verbose_name='телефон',
        unique=True,
        blank=True, null=True,
        help_text="Внесите телефон, прим. '+38212345678'. Для пустого значения, внесите 'None'.",
    )
    subscription = models.BooleanField(
        'subsription',
        default=True
    )
    language = models.CharField(
        'язык',
        max_length=10,
        choices=settings.LANGUAGES,
        default="RUS"
    )
    date_joined = models.DateTimeField(
        'Дата регистрации',
        auto_now_add=True
    )

    # дата последней активности

    notes = models.CharField(
        'Комментарии',
        max_length=400,
        blank=True, null=True
    )

    msngr_link = models.URLField(
        'Чат',
        blank=True, null=True
    )

    class Meta:
        ordering = ['-date_joined']
        verbose_name = 'Соц сети аккаунт'
        verbose_name_plural = 'Соц сети аккаунты'

    def __str__(self):
        return f'Tm id = {self.msngr_id}'

    def save(self, *args, **kwargs):
        # Автоматически генерирует ссылку на чат перед сохранением, если msngr_username изменено
        self.get_msngr_link()
        if self.msngr_type == 'wts':
            self.msngr_phone = self.msngr_username
        super().save(*args, **kwargs)

    def get_msngr_link(self):
        # Генерирует ссылку на чат в мессенджере на основе msngr_username
        # В данном примере, предполагается, что вы используете Telegram
        if self.msngr_type == 'tm':
            username = self.msngr_username[1:]
            self.msngr_link = (
                f"<a href='https://t.me/{username}'"
                f" target='_blank'>Открыть чат (Tm)</a>"
            )

        if self.msngr_type == 'wts':
            username = self.msngr_username
            self.msngr_link = (
                f"<a href='https://wa.me/{username}'"
                f" target='_blank'>Открыть чат (Wts)</a>"
            )


class Message(models.Model):
    profile = models.ForeignKey(
        to=MessengerAccount,
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



# class MessengerAccount(models.Model):
#     # создать метод очистки сохряняемых данных

#     tm_id = models.CharField(
#         'Telegram_ID',
#         max_length=100,
#         validators=[MinLengthValidator(4)],
#         blank=True
#     )
#     tm_username = models.CharField(
#         'Telegram_Username',
#         max_length=100,
#         validators=[MinLengthValidator(1)],
#         blank=True, null=True
#     )
#     tm_subscription = models.BooleanField(
#         'Telegram_subsription',
#         default=True
#     )
#     tm_language = models.CharField(
#         'Telegram_язык',
#         max_length=10,
#         choices=settings.LANGUAGES,
#         default="RUS"
#     )
#     date_joined = models.DateTimeField(
#         'Дата регистрации', auto_now_add=True
#     )

#     # дата последней активности

#     notes = models.CharField(
#         'Пометки',
#         max_length=400,
#         blank=True, null=True
#     )

#     class Meta:
#         ordering = ['-date_joined']
#         verbose_name = 'Telegram аккаунт'
#         verbose_name_plural = 'Telegram аккаунты'

#     def __str__(self):
#         return f'Tm id = {self.tm_id}'


# class Message(models.Model):
#     profile = models.ForeignKey(
#         to=MessengerAccount,
#         verbose_name='Профиль',
#         on_delete=models.PROTECT,
#     )
#     text = models.TextField(
#         verbose_name='Текст',
#     )
#     created_at = models.DateTimeField(
#         verbose_name='Время получения',
#         auto_now_add=True,
#     )

#     def __str__(self) -> str:
#         return f'Сообщение {self.pk} от {self.profile}'

#     class Meta:
#         verbose_name = 'Сообщение'
#         verbose_name_plural = 'Сообщения'
