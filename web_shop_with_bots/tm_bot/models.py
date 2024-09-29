from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from tm_bot.validators import validate_msngr_username
from catalog.models import Dish
from delivery_contacts.models import Delivery, Restaurant
import logging
from delivery_contacts.services import (
    google_validate_address_and_get_coordinates,
    get_delivery_cost_zone
)
from django import forms
from decimal import Decimal
from django.db.models import Sum


logger = logging.getLogger(__name__)


class AdminChatTM(models.Model):
    chat_id = models.CharField(
        'ID чата в ТМ',
        max_length=100,
        validators=[MinLengthValidator(4)],
        unique=True,
        blank=True, null=True,
        help_text="Получить через BotFather."
    )
    city = models.CharField(
        max_length=40,
        verbose_name="город *",
        choices=settings.CITY_CHOICES,
        default=settings.DEFAULT_CITY,
        blank=True, null=True,
    )
    restaurant = models.OneToOneField(
        Restaurant,
        on_delete=models.PROTECT,
        verbose_name='ресторан',
        related_name='admin_chat',
        default=settings.DEFAULT_RESTAURANT,
        blank=True, null=True
    )

    class Meta:
        ordering = ['city']
        verbose_name = 'Админ-чат TM'
        verbose_name_plural = 'Админ-чаты TM'


class OrdersBot(models.Model):
    msngr_type = models.CharField(
        'msngr typ',
        max_length=3,
        choices=settings.MESSENGERS,
    )
    name = models.CharField(
        'Название',
        max_length=100,
        validators=[MinLengthValidator(4)],
        unique=True,
        blank=True, null=True,
    )
    msngr_id = models.CharField(
        'ID бота в ТМ',
        max_length=100,
        validators=[MinLengthValidator(4)],
        unique=True,
        blank=True, null=True,
        help_text="Получить через BotFather."
    )
    source_id = models.CharField(
        'ID на платформе',
        max_length=100,
        validators=[MinLengthValidator(4)],
        unique=True,
        blank=True, null=True,
        help_text="ID бота на платформе ботов."
    )
    city = models.CharField(
        max_length=40,
        verbose_name="город *",
        choices=settings.CITY_CHOICES,
        default=settings.DEFAULT_CITY,
        unique=True,
        blank=True, null=True,
    )
    link = models.URLField(
        max_length=200,
        help_text='Стандартная ссылка на бота.'
    )
    frontend_link = models.URLField(
        max_length=200,
        help_text=("Сссылка для отображения на сайте.<br>"
                   "Собирает статистику по клиентам, которые перешли с сайта.")
    )
    is_active = models.BooleanField(
        verbose_name='активен',
        default=False,
        help_text='Активный чат отображается на сайте.'
    )
    api_key = models.CharField(
        max_length=100,
        verbose_name=("API ключ д/синхронизации информации о заказах<br>"
                      "изменению статуса заказа через админку)"),
        blank=True, null=True
    )

    class Meta:
        ordering = ['city']
        verbose_name = 'Бот д/приема заказов'
        verbose_name_plural = 'Боты д/приема заказов'


class MessengerAccount(models.Model):
    # создать метод очистки сохраняемых данных
    msngr_type = models.CharField(
        _('msngr type  *'),
        max_length=3,
        choices=settings.MESSENGERS,
    )
    msngr_id = models.CharField(
        'ID',
        max_length=100,
        validators=[MinLengthValidator(4)],
        unique=True,
        blank=True, null=True,
        help_text="Только для Tm, внесется автоматически."
    )
    tm_chat_id = models.CharField(
        'Tm_chat_ID',
        max_length=100,
        validators=[MinLengthValidator(4)],
        blank=True, null=True,
        help_text="Только для Tm, внесется автоматически."
    )
    msngr_username = models.CharField(
        'Username  *',
        max_length=100,
        validators=[validate_msngr_username,],
        # unique=True, изменяемо, может быть ''
        help_text=(
            "Для Tm username начинается с @. ( прим '@yume_sushi')<br>"
            "Для Wts username = номер телефона. (прим '+38212345678')<br>"
            "Для Vbr username = номер телефона. (прим '+38212345678')")
    )
    msngr_first_name = models.CharField(
        'Имя',
        max_length=150,
        blank=True, null=True
        )
    msngr_last_name = models.CharField(
        'Фамилия',
        max_length=150,
        blank=True, null=True
        )
    msngr_phone = PhoneNumberField(
        verbose_name='Телефон',
        unique=True,
        blank=True, null=True,
        help_text=("Внесите телефон, прим. '+38212345678'. "
                   "Для пустого значения, внесите 'None'.")
    )
    subscription = models.BooleanField(
        'Подписка на рассылки',
        default=True
    )
    registered = models.BooleanField(
        'Регистрация на сайте',
        default=False
    )
    language = models.CharField(
        'Язык',
        max_length=10,
        choices=settings.LANGUAGES,
        default=settings.DEFAULT_CREATE_LANGUAGE
    )
    created = models.DateTimeField(
        'Дата регистрации',
        auto_now_add=True
    )

    # дата последней активности

    notes = models.TextField(
        'Комментарии',
        max_length=400,
        blank=True, null=True
    )

    msngr_link = models.URLField(
        'Текст ссылки в Чат',
        blank=True, null=True,
        help_text="Ссылка на чат, внесется автоматически."
    )
    city = models.CharField(
        max_length=40,
        verbose_name="город *",
        choices=settings.CITY_CHOICES,
        default=settings.DEFAULT_CITY,
        blank=True, null=True,
    )
    # в админке поле не используется, т.к. необходимо HTML форматирование

    class Meta:
        ordering = ['-created']
        verbose_name = 'Соц сети аккаунт'
        verbose_name_plural = 'Соц сети аккаунты'

    def __str__(self):

        return (f"{self.msngr_username}({self.msngr_type})")   #  "
                #f"{self.msngr_first_name if self.msngr_first_name is not None else ''} "
                #f"{self.msngr_last_name if self.msngr_last_name is not None else ''}")

    def save(self, *args, **kwargs):
        # Проверяем, создаем ли мы новый объект или обновляем существующий
        if self.pk is not None:
            for attr, value in kwargs.items():
                setattr(self, attr, value)

        # Вызываем метод get_msngr_link() и производим дополнительные действия
        self.get_msngr_link()
        if self.msngr_type == 'wts':
            self.msngr_phone = self.msngr_username
        try:
            super().save(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"An error occurred while saving the MessengerAccount: {e}")

        return self

    def get_msngr_link(self):
        # Генерирует ссылку на чат в мессенджере на основе msngr_username
        # В данном примере, предполагается, что вы используете Telegram
        if self.msngr_username == '':
            self.msngr_link = ''

        elif self.msngr_type == 'tm':
            username = self.msngr_username[1:]
            self.msngr_link = (
                f"<a href='https://t.me/{username}'"
                f" target='_blank'>чат {username}(Tm)</a>"
            )

        elif self.msngr_type == 'wts':
            username = self.msngr_username
            self.msngr_link = (
                f"<a href='https://wa.me/{username}'"
                f" target='_blank'>чат {username}(Wts)</a>"
            )

    @staticmethod
    def fulfill_messenger_account(messenger_account):
        msngr_username = messenger_account['msngr_username']
        if msngr_username[0] == '+':
            messenger_account['msngr_type'] = 'wts'
        elif msngr_username[0] == '@':
            messenger_account['msngr_type'] = 'tm'
        return messenger_account

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

    def reset_telegram_account_info(self):
        old_notes = self.notes if self.notes else ""
        new_notes = (
            f"Удаление юзернейма и линка во избежании конфликта с новыми "
            f"пользователями. "
            f"Старый username: {self.msngr_username}."
        )
        self.notes = f"{old_notes}\n{new_notes}".strip()
        self.msngr_username = ''
        self.msngr_link = ''
        self.save()

    def get_orders_data(self):
        if hasattr(self, 'orders'):
            orders_aggregate = self.orders.aggregate(
                total_sum=Sum('final_amount_with_shipping'))
            total_sum = orders_aggregate.get('total_sum', 0) or 0
            orders_qty = self.orders.count()
        else:
            total_sum = 0
            orders_qty = 0
        return f"{total_sum} rsd ({orders_qty} зак.)"


def msgr_account_unique(value):
    if value:
        ma = MessengerAccount.objects.filter(msngr_username=value).first()
        if ma:
            raise ValidationError("Such account already exists.")


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


def get_delivery_data_tmbot(self, data, city, amount):
    process_comment = ''
    delivery = get_delivery_tmbot(data.get("delivery[type]"), city)
    address = data.get('address')

    delivery_zone, coordinates, delivery_cost = None, None, Decimal(0)

    if delivery.type == 'delivery':
        try:
            if address != '':
                lat, lon, status = google_validate_address_and_get_coordinates(
                                    address, city)
            elif data.get('comment') != '':
                address = data.get('comment')
                lat, lon, status = google_validate_address_and_get_coordinates(
                                    address, city)
            else:
                lat, lon = None, None

        except ValidationError:
            lat, lon = None, None

        delivery_cost, delivery_zone = get_delivery_cost_zone(
                                            city,
                                            amount, delivery,
                                            lat, lon)
        coordinates = f"{lat}, {lon}"
    return (delivery, delivery_zone, coordinates,
            delivery_cost, address, process_comment)


def get_delivery_tmbot(tmbot_deliv_type, city):
    if tmbot_deliv_type == 'pickup':
        return Delivery.objects.get(city=city, type='takeaway')
    elif tmbot_deliv_type == 'courier':
        return Delivery.objects.get(city=city, type='delivery')
    else:
        logging.error(f"Delivery with id {tmbot_deliv_type} is not found")


def get_time_tmbot(tmbot_time):
    process_comment = ''
    time = None
    if tmbot_time in ['', 'как можно скорее']:
        time_comment = ''
    else:
        time_comment = str(tmbot_time)
    return time, time_comment, process_comment


def get_orderdishes_tmbot(self, data):
    if data is None:
        logging.error("Goods list is empty.")
        return None
    process_comment = ''
    orderdishes = []
    amount = 0
    index = 0
    items_qty = 0

    article = data.get(f'goods[{index}][article]')
    while article is not None:
        try:
            dish = Dish.objects.get(article=article)
        except Dish.DoesNotExist:
            try:
                title = data.get(f'goods[{index}][title]')
                dish = Dish.objects.get(translations__msngr_short_name=title)

            except Dish.DoesNotExist:
                logging.error(f"Dish with article {article} and title "
                              f"{title} is not found")
                process_comment += (
                    f"Блюдо арт '{article}'/ "
                    f"назв '{title}' не найдено, не сохранено.\n")
                index += 1
                article = data.get(f'goods[{index}][article]')
                continue

        count = int(float(data.get(f'goods[{index}][count]')))
        orderdishes.append({'dish': dish,
                            'quantity': count})
        unit_amount = dish.final_price * count
        amount += unit_amount
        items_qty += count    #!!!!!
        index += 1
        article = data.get(f'goods[{index}][article]')

    return orderdishes, amount, items_qty, process_comment


def get_tm_user(self, data):
    process_comment = ''
    msngr_id = data.get('user_telegram[id]')
    msngr_account = MessengerAccount.objects.filter(
                                              msngr_type='tm',
                                              msngr_id=msngr_id).first()
    user_telegram_data = {}
    if msngr_account is None:
        user_telegram_data = {
            "tm_chat_id": data.get("user_chat_id"),
            "msngr_first_name": data.get('user_telegram[first_name]'),
            "msngr_id": msngr_id,
            "msngr_last_name": data.get('user_telegram[last_name]'),
            "msngr_username": data.get('user_telegram[username]')
        }

    return msngr_account, user_telegram_data, process_comment


def get_promocode_tmbot(self, data):
    pass


def get_status_tmbot(tmbot_status):
    if tmbot_status == 'ожидает обработки':
        status = "WCO"
    elif tmbot_status == 'подтвержден':
        status = "CFD"
    elif tmbot_status == 'отправлен получателю':
        status = "OND"
    elif tmbot_status in ['доставлен', 'выдан']:
        status = "DLD"
    elif tmbot_status in ['отменен', 'недозвон']:
        status = "CND"
    else:
        status = None
    return status


def get_city_tmbot(shop_id):
    bot = OrdersBot.objects.filter(source_id=shop_id).first()
    if bot:
        return bot.city
    return settings.DEFAULT_CITY


def get_bot(data):
    shop_id = data.get("shop[id]")
    bot = OrdersBot.objects.get(source_id=shop_id)
    # if bot:
    #     if bot.api_key is not None and not api_key_is_valid(bot, data):
    #         return ValidationError("API key isn't correct")

    return bot


def api_key_is_valid(bot, data):
    return bot.api_key == data.get("API")
