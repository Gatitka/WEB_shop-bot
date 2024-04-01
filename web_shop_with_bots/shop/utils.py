from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


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


def get_first_item_true(obj):
    # проверка на первый заказ
    model_class = obj.__class__
    if obj.user is not None:
        if not model_class.objects.filter(user=obj.user).exists():
            return True
    else:
        if not model_class.objects.filter(
            recipient_phone=obj.recipient_phone
        ).exists():
            return True
    return False
