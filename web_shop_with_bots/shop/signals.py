from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from shop.services import find_uncomplited_cart_to_complete
from shop.models import Order


@receiver(post_save, sender=Order)
def create_cart(sender, instance, created, **kwargs):
    """ Создание ShoppingCart при создании BaseProfile"""
    if created:
        if instance.user is not None:
            find_uncomplited_cart_to_complete(instance.user)
