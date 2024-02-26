from django.conf import settings
from django.contrib.auth.models import AbstractUser
# from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
import requests
from django.db.models.signals import post_save
from django.dispatch import receiver

# from users.models import BaseProfile

MESSENGERS = [
    ('tm', 'Telegram'),
    ('wts', 'WhatsApp'),
    ('vb', 'Viber'),
]


class MessengerAccount(models.Model):
    # создать метод очистки сохраняемых данных
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
    tm_chat_id = models.CharField(
        'Tm_chat_ID',
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
        # Проверяем, создаем ли мы новый объект или обновляем существующий
        if self.pk is not None:
            for attr, value in kwargs.items():
                setattr(self, attr, value)

        # Вызываем метод get_msngr_link() и производим дополнительные действия
        self.get_msngr_link()
        if self.msngr_type == 'wts':
            self.msngr_phone = self.msngr_username
        super().save()

        return self

    def get_msngr_link(self):
        # Генерирует ссылку на чат в мессенджере на основе msngr_username
        # В данном примере, предполагается, что вы используете Telegram
        if self.msngr_type == 'tm':
            username = self.msngr_username[1:]
            self.msngr_link = (
                f"<a href='https://t.me/{username}'"
                f" target='_blank'>Открыть чат (Tm)</a>"
            )

        elif self.msngr_type == 'wts':
            username = self.msngr_username
            self.msngr_link = (
                f"<a href='https://wa.me/{username}'"
                f" target='_blank'>Открыть чат (Wts)</a>"
            )

    def send_message_to_telegram(self, username, message):
        # Получаем chat_id пользователя по его юзернейму
        # token = settings.BOT_TOKEN
        # url = f'https://api.telegram.org/bot{token}/getChat'
        # params = {'chat_id': username}
        # response = requests.get(url, params=params)
        # data = response.json()
        # chat_id = data['result']['id']  # Получаем chat_id пользователя
        # # chat_id = '194602954'
        # # Отправляем сообщение пользователю
        # url = f'https://api.telegram.org/bot{token}/sendMessage'
        # payload = {
        #     'chat_id': chat_id,
        #     'text': message
        # }
        # response = requests.post(url, data=payload)
        # return response.json()
        pass


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


@receiver(post_save, sender=MessengerAccount)
def create_messenger_account(sender, instance, **kwargs):
    message = 'Спасибо! теперь мы будем держать вас в курсе событий!'
    instance.send_message_to_telegram(instance.msngr_username, message)


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
