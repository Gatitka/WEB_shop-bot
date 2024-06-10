from django.conf import settings
import requests
from parler.utils.context import switch_language
from django.utils import timezone
from exceptions import BotMessageSendError
import logging


logger = logging.getLogger(__name__)


def send_message_new_order(instance):
    """ Отправка сообщения телеграм-ботом в админский чат
        о новом заказе на сайте."""

    message = get_message(instance)
    return send_message_telegram(settings.CHAT_ID, message)


def get_message(instance):
    order_data = get_order_data(instance)

    user_data = get_user_data(instance)

    delivery_data = get_delivery_data(instance)

    orderdishes_data = get_orderdishes_data(instance)

    comment_data = get_comment_data(instance)

    total_data = get_total_data(instance)

    message = (
        f"❗️**Заказ на сайте** 'Yume Sushi':\n"
        f"{order_data}"

        "👉 Данные покупателя:\n"
        # Diana, +384677436384,
        # (Tm) @Diana_Dernovici, (1 зак)
        f"{user_data}"

        "📦 Доставка:\n"
        # Адрес: Врачар,Кумановска 24, кв 5
        # Время: К 18:30
        f"{delivery_data}\n"

        "📝 Комментарий:\n"
        # Заказ ко времени, на 18:30. Оплата наличными. Если интерфон не сработает сразу,просьба курьеру набрать меня
        f"{comment_data}\n"

        "---\n"
        "🛒 Товары:\n"
        # 1. Ролл Хоккайдо 1x1 000 din = 1 000 din
        f"{orderdishes_data}"

        "**---**\n"
        f"{total_data}"
    )
    return message


def get_order_data(instance):
    """ Номер #1. ПЕРВЫЙ ЗАКАЗ."""
    first_order = ""
    if instance.is_first_order:
        first_order = 'ПЕРВЫЙ ЗАКАЗ'

    return f"Номер #{instance.order_number}. {first_order}\n\n"


def get_user_data(instance):
    """ # Diana, +384677436384,
        # (Tm) @Diana_Dernovici, (1 зак)  🙋‍♂️👤"""
    msngr_acc_rep = ''
    user_icon = '👤'

    if instance.user:
        orders_qty = instance.user.orders_qty
        if instance.user.messenger_account:
            msngr_acc = instance.user.messenger_account
            msngr_acc_rep = (
                f"({msngr_acc.msngr_type}) {msngr_acc.msngr_username}, ")

        msngr_acc_and_orders = (
            f"{msngr_acc_rep}({orders_qty} зак)\n")
    else:
        msngr_acc_and_orders = ''

    return (f"{user_icon} {instance.recipient_name}, "
            f"{instance.recipient_phone} \n "
            f"{msngr_acc_and_orders}\n")


def get_delivery_data(instance):
    """🚗 Привезти
        Адрес: Ravanička 29, ap 4 ,sprat 1
        Время: как можно скорее"""
    if instance.delivery.type == 'delivery':
        delivery_data = (
            "🚗 Привезти\n"
            f"Адрес: {instance.recipient_address}\n"
        )

    elif instance.delivery.type == 'takeaway':
        delivery_data = "🛍️ Самовывоз\n"

    delivery_time = instance.delivery_time
    if delivery_time:
        current_time = timezone.now()
        # Проверяем, является ли delivery_time сегодняшним днем
        if instance.delivery_time.date() == current_time.date():
            # Если delivery_time сегодня, возвращаем только время
            delivery_time = (f"Время: сегодня к "
                             f"{instance.delivery_time.strftime('%H:%M')}\n")
        else:
            # Если delivery_time в будущем, возвращаем дату и время
            delivery_time = (f"Время: "
                             f"{instance.delivery_time.strftime('%d-%m-%Y- %H:%M')}\n")
    else:
        delivery_time = "Время: как можно скорее\n"

    return (delivery_data + delivery_time)


def get_comment_data(instance):
    """#Заказ ко времени, на 18:30. Оплата наличными.
    Если интерфон не сработает сразу,просьба курьеру набрать меня"""
    comment = instance.comment if instance.comment is not None else ""
    comment_data = (
        f"Оплата {instance.payment_type}. {comment}"
    )
    return comment_data


def get_orderdishes_data(instance):
    orderdishes = ''
    num = 1

    for orderdish in instance.orderdishes.all():
        dish = orderdish.dish
        with switch_language(dish, 'ru'):
            short_name = orderdish.dish.short_name
            # Получаем перевод short_description на указанный язык

        str = (f"#{num}. {short_name} "
               f"{orderdish.quantity}x{orderdish.unit_price} rsd"
               f"= {orderdish.unit_amount}\n")
        num += 1
        orderdishes += str

    return orderdishes


def get_total_data(instance):
    """Товары: 2 150 din
        Доставка: 0 din
        Итого: 2 150 din"""

    # доставка
    delivery_cost = f"{instance.delivery_cost} rsd\n"
    if instance.delivery.type == 'delivery':
        if instance.delivery_zone.name == 'уточнить':
            delivery_cost = "уточнить!!!\n"

    # итого
    if delivery_cost == "уточнить!!!\n":
        total = f"{instance.final_amount_with_shipping} rsd БЕЗ ДОСТАВКИ!!!"
    else:
        total = f"{instance.final_amount_with_shipping} rsd"

    total_data = (
        f"Товары: {instance.discounted_amount} rsd\n"
        f"Доставка: {delivery_cost}"
        f"Итого: {total}")

    return total_data


def send_error_message_order_unsaved(order_id, e):
    """ Отправка сообщения телеграм-ботом в админский чат
        о том, что заказ из бота не сохранился."""

    message = f'Заказ TM BOT #{order_id} не сохранился в базе данных.'
    send_message_telegram(settings.CHAT_ID, message)


def send_error_message_order_saved(order_id):
    """ Отправка сообщения телеграм-ботом в админский чат
        о том, что заказ из бота сохранился но с ошибками."""

    message = f'! Заказ TM BOT #{order_id} сохранился с ошибками.'
    send_message_telegram(settings.CHAT_ID, message)


def send_message_telegram(chat_id, message):
    # Отправляем сообщение
    url = f'https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    response = requests.post(url, data=payload)
    response = response.json()
    if response['ok'] is False:
        raise BotMessageSendError(
            f"Failed to send telegram message {message}: "
            f"{response}")


def send_request_order_status_update(new_status, order_id):
    token = settings.BOTOBOT_API_KEY
    #token = settings.BOT_TOKEN
    url = f"https://www.botobot.ru/api/v1/updateOrderStatus/{token}"

    if new_status == 'WCO':
        status = 10
    elif new_status == "CFD":
        status = 20
    elif new_status == "OND":
        status = 70
    elif new_status == "DLD":
        status = 90
    elif new_status == "CND":
        status = 30

    payload = {'id': order_id,
               'status': status}
    try:
        # Отправка POST-запроса
        response = requests.post(url, data=payload)
        response_data = response.json()
        reply_status = response_data.get('status')
        # Обработка ответа
        if response.status_code == 200 and reply_status == 'success':
            logger.info(f"TM order {order_id} "
                        f"status updated to {new_status} "
                        f"(status: {reply_status}).")
        else:
            error_message = response_data.get('message',
                                              'No error message provided')
            logger.error(f"Failed to update TM order {order_id} status to "
                         f"{new_status} "
                         f"(status: {reply_status}): {error_message}")

    except requests.RequestException as e:
        # Логирование ошибки запроса
        logger.error(f"Sending request failed for order {order_id} "
                     f"with status {new_status} (status: {str(e)}")
