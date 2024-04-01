from datetime import date

from django.db.models import Max
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

from .models import Dish


@receiver(pre_save, sender=Dish)
def reset_order_number(sender, instance, **kwargs):
    if instance.pk is None:  # Проверяем, что это новый заказ
        max_dish_id = Dish.objects.filter(
            category=instance.category
        ).aggregate(Max('dish_id'))['dish_id__max'] or 0
        # Устанавливаем номер заказа на единицу больше MAX текущей даты
        instance.id = max_dish_id + 1
