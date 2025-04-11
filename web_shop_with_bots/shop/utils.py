"""Вспомогательные функции для общей работы с моделями shop.models"""
from django.db.models import Max
from django.utils import timezone

from datetime import timedelta


def get_execution_date(pk, execution_date, delivery_time, created):
    # при сохранении заказа из всех источников опрееляется дата исполнения
    new_order_num = False
    if pk is None:
        if delivery_time:
            execution_date = delivery_time.date()
        else:
            execution_date = timezone.localtime().date()

    else:
        if delivery_time or execution_date is None:
            if delivery_time is None and execution_date is None:
                new_execution_date = created.date()
            if delivery_time:
                new_execution_date = delivery_time.date()

            if execution_date != new_execution_date:
                execution_date = new_execution_date
                new_order_num = True

    return execution_date, new_order_num


def get_next_item_id(model, field, restaurant, execution_date):
    # при сохранении заказа из всех источников новый номер заказа
    max_id = model.objects.filter(
        execution_date=execution_date,     # (today_start, today_end),
        restaurant=restaurant
    ).aggregate(Max(field))[f'{field}__max']

    # Устанавливаем номер заказа на единицу больше MAX текущей даты
    if max_id is None:
        return 1
    else:
        return max_id + 1


# def get_next_item_id_today_model(model, field):
#     today_start = timezone.localtime(
#         timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0)
#     # Начало текущего дня

#     today_end = (
#         today_start + timezone.timedelta(days=1)
#         - timezone.timedelta(microseconds=1)  # Конец текущего дня
#     )

#     max_id = model.objects.filter(
#         created__range=(today_start, today_end)
#     ).aggregate(Max(field))[f'{field}__max']

#     # Устанавливаем номер заказа на единицу больше MAX текущей даты
#     if max_id is None:
#         return 1
#     else:
#         return max_id + 1


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
