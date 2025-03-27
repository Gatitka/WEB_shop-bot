from django.db.models import Max
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from datetime import timedelta


def get_next_item_id_today(model, field, restaurant):
    today_start = timezone.localtime(
        timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    # Начало текущего дня

    today_end = (
        today_start + timezone.timedelta(days=1)
        - timezone.timedelta(microseconds=1)  # Конец текущего дня
    )

    max_id = model.objects.filter(
        created__range=(today_start, today_end),
        restaurant=restaurant
    ).aggregate(Max(field))[f'{field}__max']

    # Устанавливаем номер заказа на единицу больше MAX текущей даты
    if max_id is None:
        return 1
    else:
        return max_id + 1


def get_next_item_id_today_model(model, field):
    today_start = timezone.localtime(
        timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    # Начало текущего дня

    today_end = (
        today_start + timezone.timedelta(days=1)
        - timezone.timedelta(microseconds=1)  # Конец текущего дня
    )

    max_id = model.objects.filter(
        created__range=(today_start, today_end)
    ).aggregate(Max(field))[f'{field}__max']

    # Устанавливаем номер заказа на единицу больше MAX текущей даты
    if max_id is None:
        return 1
    else:
        return max_id + 1


def get_first_order_true(obj):
    """Проверка на первый заказ только для заказов с сайта source='4'."
       Если есть зареганый юзер, то проверяется наличие у него заказаов.
       Если юзера нет, то проверяется наличие заказов по телефону, для того чтобы
       в админке отразить, что это первый заказ незарега и
       его нужно переориентировать на сайт."""

    model_class = obj.__class__
    if obj.source == '4' and obj.created_by == 1:
        if obj.user is not None:
            if not model_class.objects.filter(user=obj.user).exists():
                return True
        else:
            if not model_class.objects.filter(
                recipient_phone=obj.recipient_phone
            ).exists():
                return True
    return False


def split_and_get_comment(input_string):
    # Разделение строки по подстроке "comment from user:"
    parts = input_string.split(",  comment from user:")

    # Если подстрока найдена
    if len(parts) > 1:
        # Получение всех символов до подстроки
        address_comment = parts[0].strip()
        comment = parts[1].strip()
    else:
        address_comment, comment = None, None

    return address_comment, comment


# 'flat: 5, floor: 5, interfon: 5,  comment from user:5\\57'

def get_flag(instance):
    if instance.language == 'ru':
        flag = 'RU'
    elif instance.language == 'en':
        flag = 'EN'
    else:
        flag = 'RS'
    return flag


def custom_source(obj):
    # краткое название поля в list
    source_id = f'#{obj.source_id}' if obj.source_id is not None else ''
    source = obj.get_source_display()
    if source == "TM_Bot" and obj.orders_bot_id:
        source = f"{source}{obj.orders_bot_id}"
    if obj.status == 'WCO':
        return format_html(
            '<span style="color:green; font-weight:bold;">{}<br>{}</span>',
            source, source_id)

    return format_html('{}<br>{}', source, source_id)


def custom_order_number(obj):
    # Создаем URL для редактирования заказа
    edit_url = reverse('admin:shop_order_change', args=[obj.pk])
    # Форматируем текст ссылки и возвращаем его
    return format_html('<a href="{}">{} /{}</a>',
                       edit_url, obj.order_number, obj.id)


def get_delivery_time_if_none(delivery_time,
                              min_time, max_time,
                              current_time,
                              deliv_min_time=None):

    if min_time <= delivery_time <= max_time:
        return None

    if min_time > delivery_time:
        # если время вне работы и до открытия, то день тот же
        if deliv_min_time:
            value = current_time.replace(
                hour=deliv_min_time.hour,
                minute=deliv_min_time.minute,
                second=0,
                microsecond=0
            )

        else:
            value = current_time.replace(
                hour=min_time.hour,
                minute=min_time.minute,
                second=0,
                microsecond=0
            )

    elif max_time < delivery_time:
        # если время вне работы и после закрытия, то +1 день
        tomorrow = current_time + timedelta(days=1)
        if deliv_min_time:
            value = tomorrow.replace(
                hour=deliv_min_time.hour,
                minute=deliv_min_time.minute,
                second=0,
                microsecond=0
            )
        else:
            value = tomorrow.replace(
                hour=min_time.hour,
                minute=min_time.minute,
                second=0,
                microsecond=0
            )

    return value
