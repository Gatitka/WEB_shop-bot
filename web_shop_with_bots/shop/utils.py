from django.db.models import Max
from django.utils import timezone


def get_next_item_id_today(model, field):
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


def get_first_item_true(obj):
    # проверка на первый заказ только для заказов с сайта source='4'
    model_class = obj.__class__
    if obj.source == '4':
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
