from delivery_contacts.utils import get_translate_address_comment
from parler.utils.context import switch_language
from django.utils import timezone
import re
from html import unescape
import random


STATUS_CHANGED_MESSAGES = {
    "CFD": [
        "Заказ подтверждён — скоро будет вкусно 😋",
        "Заказ подтвержден! Начинаем готовить прямо сейчас 🍣",
        "Заказ подтвержден! Готовим с улыбкой и скоростью ниндзя 🥷",
        "Подтверждено! Наши повара уже в боевой стойке 🥷🍣",
        "Заказ принят! Вас ожидает порция счастья 😍",
        ],
    "OND": [
        "Уже в пути! 🚚 Скоро постучим в дверь.",
        "Ваш заказ отправлен — держитесь, вкусное рядом 😉",
        "Ваш заказ в дороге — готовьтесь принимать вкусное 🎁",
        "Заказ уже едет к вам! 🚴‍♂️",
        "Отправили! Курьер несёт вкусное прямо к вам 🏃‍♂️",
        "В пути! Откройте сердце (и дверь) для суши ❤️🚪",
        "Доставляется! Еда уже ближе, чем кажется 😉",
    ],
    "RDY": [
        "Готово! 🍣 Можно забирать — мы уже ждём вас 😉",
        "Ваш заказ собран и ждёт вас! 🍣",
        "Мы всё приготовили — можно забирать! 🥢",
    ]
}


def get_admin_message_new_order(instance):
    source_data = get_source_data(instance)

    order_data = get_order_data(instance)

    user_data = get_user_data(instance)

    delivery_data = get_delivery_data(instance)

    orderdishes_data = get_orderdishes_data(instance)

    comment_data = get_comment_data(instance)

    total_data = get_total_data(instance)

    process_comment= get_process_comment(instance)

    message = (
        # """❗️Заказ на сайте 'Yume Sushi':""""
        # "" Номер #1. ПЕРВЫЙ ЗАКАЗ."""

        f"{source_data}:\n"
        f"{order_data}\n\n"

        "👉 Данные покупателя:\n"
        # Diana, +384677436384,
        # (Tm) @Diana_Dernovici, (1 зак)
        f"{user_data}"

        "📦 Способ получения:\n"
        # Адрес: Врачар,Кумановска 24, кв 5
        # Время: К 18:30
        f"{delivery_data}\n"

        "📝 Комментарий:\n"
        # Заказ ко времени, на 18:30. Оплата наличными. Если интерфон не сработает сразу,просьба курьеру набрать меня
        f"{comment_data}\n"

        "---\n"
        "🛒 Блюда:\n"
        # 1. Ролл Хоккайдо 1x1 000 din = 1 000 din
        f"{orderdishes_data}"

        "---\n"
        f"{total_data}"
        f"{process_comment}"
    )
    return message


def get_source_data(instance):
    """❗️Заказ на сайте 'Yume Sushi':"""
    if instance.source == '4':
        return "❗️Заказ на сайте 'Yume Sushi'"
    if instance.source == '3':
        bot = instance.orders_bot
        return f"❗️Заказ из бота '{bot.name}'"
    else:
        return "❗️Заказ от Администратора"


def get_order_data(instance):
    """ Номер #1. ПЕРВЫЙ ЗАКАЗ."""
    first_order = ""
    if instance.is_first_order:
        if instance.user:
            first_order = 'ПЕРВЫЙ ЗАКАЗ'
        else:
            first_order = 'Гость (не авторизован)'
    if instance.source == '3':
        if instance.user:
            if instance.user.orders_qty == 0:
                first_order = 'ПЕРВЫЙ ЗАКАЗ'
    return f"Номер #{instance.order_number}. {first_order}"


def get_user_data(instance):
    """ # Diana, +384677436384,
        # (Tm) @Diana_Dernovici, (1 зак)  🙋‍♂️👤"""
    msngr_acc_rep = ''
    user_icon = ''

    if instance.user:
        orders_qty = instance.user.orders_qty + 1
        if instance.user.messenger_account:
            msngr_acc = instance.user.messenger_account

            if msngr_acc.msngr_type == 'tm':
                if msngr_acc.msngr_username:
                    msngr_link = "@{}".format(msngr_acc.msngr_username)
                else:
                    msngr_link = 'username отсутствует'
            if msngr_acc.msngr_type == 'wts':
                msngr_link = msngr_acc.msngr_username

            msngr_acc_rep = (
                f"({msngr_acc.msngr_type}) {msngr_link}, ")
        msngr_acc_and_orders = (
            f"{msngr_acc_rep}({orders_qty}-й заказ)\n")
        user_icon = '👤'

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
        city = instance.get_city_short()
        address_com = get_translate_address_comment(instance.address_comment)
        if len(address_com) > 100:
            address_com = address_com[100:] + '...'
        delivery_data = (
            "🚗 Привезти\n"
            f"Адрес: ({city}), {instance.recipient_address}, "
            f"{address_com}\n"
        )

    elif instance.delivery.type == 'takeaway':
        delivery_data = "🛍️ Самовывоз\n"

    elif instance.delivery.type == 'restaurant':
        delivery_data = "🍽️ Ресторан\n"

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
                             f"{instance.delivery_time.strftime('%d.%m.%Y %H:%M')}\n")
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

    orderdishes += f"Приборы: {instance.items_qty}\n"
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
        total = f"{instance.final_amount_with_shipping} rsd БЕЗ ДОСТАВКИ!!!\n"
    else:
        total = f"{instance.final_amount_with_shipping} rsd"

    total_data = (
        f"Товары: {instance.discounted_amount} rsd\n"
        f"Доставка: {delivery_cost}"
        f"Итого: {total}")

    return total_data


def get_process_comment(instance):
    title = "\n---\n!!!ВНИМАНИЕ!!!\n"

    if instance.process_comment in [None, '']:
        process_comment = ''

    if instance.process_comment not in [None, '']:
        process_comment = (
            f"{title}"
            f"{instance.process_comment}"
        )
    if (instance.delivery.type == 'delivery'
            and instance.delivery_zone.name == 'уточнить'):

        process_comment += (
            "Зона доставки не определена или вне зон доставки.\n"
            "Уточнить адрес."
        )

    return process_comment


# -------------------------- СООБЩЕНИЯ О СТАТУСЕ ЗАКАЗА ----------------------

def get_status_message(status):
    # status_dict = settings.ORDER_STATUS_TRANSLATIONS.get(status, {})
    # status_text = status_dict.get('ru', status)
    # message = f'Ваш заказ {status_text}'
    # cleaned_message = ta.escape_markdown(message)

    msg_choices = STATUS_CHANGED_MESSAGES.get(status)
    return escape_markdown(random.choice(msg_choices))


# -------------------------- ПОДГОТОВКА ТЕКСТА ----------------------


def escape_markdown(text):
    # Символы Markdown, которые требуют экранирования
    markdown_chars = r'_*~`[]()<>#+-=|{}.!'
    # Экранируем каждый символ Markdown
    escaped_text = ''.join(f'\\{char}' if char in markdown_chars else char for char in text)
    return escaped_text


def clean_html_for_telegram(html_text):
    """
    Очищает HTML от Summernote для отправки в Telegram.
    Telegram поддерживает только: <b>, <i>, <u>, <s>, <a href="">, <code>, <pre>
    """
    if not html_text:
        return ""

    # Убираем переносы строк и лишние пробелы из HTML
    text = html_text.strip()

    # Заменяем <strong> на <b>
    text = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', text, flags=re.DOTALL)

    # Заменяем <em> на <i>
    text = re.sub(r'<em>(.*?)</em>', r'<i>\1</i>', text, flags=re.DOTALL)

    # Заменяем <del> или <strike> на <s>
    text = re.sub(r'<(del|strike)>(.*?)</\1>', r'<s>\2</s>', text, flags=re.DOTALL)

    # Обрабатываем ссылки - убираем target, class и другие атрибуты
    text = re.sub(
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        r'<a href="\1">\2</a>',
        text,
        flags=re.DOTALL
    )

    # Убираем <p>, заменяя на переносы строк
    text = re.sub(r'<p[^>]*>', '', text)
    text = re.sub(r'</p>', '\n', text)

    # Убираем <div>, <span> и другие блочные элементы
    text = re.sub(r'<div[^>]*>', '', text)
    text = re.sub(r'</div>', '\n', text)
    text = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', text, flags=re.DOTALL)

    # Убираем <br> и <br/>, заменяя на \n
    text = re.sub(r'<br\s*/?>', '\n', text)

    # Убираем все остальные неподдерживаемые теги
    allowed_tags = ['b', 'i', 'u', 's', 'a', 'code', 'pre']
    text = re.sub(
        r'<(?!\/?(' + '|'.join(allowed_tags) + r')\b)[^>]+>',
        '',
        text
    )

    # Убираем множественные переносы строк
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    # Убираем пробелы в начале и конце
    text = text.strip()

    # Декодируем HTML entities (&nbsp; и т.д.)
    text = unescape(text)

    return text
