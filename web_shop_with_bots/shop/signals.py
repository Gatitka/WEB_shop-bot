from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Order, ShoppingCart
from users.models import BaseProfile


@receiver(post_save, sender=BaseProfile)
def create_cart(sender, instance, created, **kwargs):
    """ Создание ShoppingCart при создании BaseProfile"""
    if created:
        cart, created = ShoppingCart.objects.get_or_create(user=instance)
