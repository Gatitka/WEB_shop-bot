
from django.conf import settings
from django.db.models.signals import m2m_changed, post_save, post_delete
from django.dispatch import receiver

from shop.models import Order, OrderDish
from shop.services import find_uncomplited_cart_to_complete
from tm_bot.services import send_message_new_order


@receiver(post_save, sender=Order)
def create_cart(sender, instance, created, **kwargs):
    """ Закрытие активной корзины после создания заказа."""
    if created:
        if instance.user is not None:
            find_uncomplited_cart_to_complete(instance.user)

# ДЕРЖАТЬ ВЫКЛЮЧЕНЫМ, тк сначала создается пустой заказ и до расчета скидок у клиента уже есть 1 заказ
# @receiver(post_save, sender=Order)
# def base_profile_plus_order(sender, instance, created, **kwargs):
#     """ Добавление нового заказа при сохранении."""
#     if created and instance.user:
#         instance.user.orders_qty += 1
#         instance.user.save(update_fields=['orders_qty'])


@receiver(post_delete, sender=Order)
def base_profile_minus_order(sender, instance, **kwargs):
    """Удаление 1 заказа при удалении."""
    if instance.user:
        instance.user.orders_qty -= 1
        if instance.is_first_order:
            instance.user.first_web_order = False
        instance.user.save(update_fields=['orders_qty', 'first_web_order'])


# @receiver(m2m_changed, sender=Order.dishes.through)
# def send_message_new_order_admin(sender, instance, action, **kwargs):
#     """ Отправка сообщения телеграм-ботом в админский чат
#         о новом заказе на сайте."""
#     if kwargs['action'] == 'post_add':
#         send_message_new_order(instance)
