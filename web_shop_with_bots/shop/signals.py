from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db.models import Max
from datetime import date

from .models import Order, ShoppingCart
from users.models import BaseProfile


@receiver(pre_save, sender=Order)
def reset_order_number(sender, instance, **kwargs):
    if instance.pk is None:  # Проверяем, что это новый заказ
        today = date.today()
        # Получаем максимальный номер заказа для текущей даты
        max_order_number = Order.objects.filter(
            created=today
        ).aggregate(Max('order_number'))['order_number__max'] or 0
        # Устанавливаем номер заказа на единицу больше MAX текущей даты
        instance.order_number = max_order_number + 1


@receiver(post_save, sender=BaseProfile)
def create_cart(sender, instance, created, **kwargs):
    """ Создание ShoppingCart при создании BaseProfile"""
    if created:
        cart, created = ShoppingCart.objects.get_or_create(user=instance)
