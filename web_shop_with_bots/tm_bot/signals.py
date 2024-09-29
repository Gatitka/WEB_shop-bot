from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import Permission, ContentType
from django.dispatch import receiver
from .models import AdminChatTM, OrdersBot


@receiver(post_save, sender=AdminChatTM)
def create_admin_chat_permissions(sender, instance, created, **kwargs):
    if created:
        content_type = ContentType.objects.get_for_model(AdminChatTM)

        # Создаем разрешение на изменение
        change_permission = Permission.objects.create(
            codename=f'change_adminchat_{instance.restaurant_pk}',
            name=f'Can change AdminChat {instance.restaurant_pk}',
            content_type=content_type
        )


@receiver(post_delete, sender=AdminChatTM)
def delete_admin_chat_permissions(sender, instance, **kwargs):
    # Удаляем пермишены, связанные с этим объектом
    Permission.objects.filter(
        codename=f'change_adminchat_{instance.restaurant_pk}').delete()


@receiver(post_save, sender=OrdersBot)
def create_orders_bot_permissions(sender, instance, created, **kwargs):
    if created:
        content_type = ContentType.objects.get_for_model(AdminChatTM)

        # Создаем разрешение на изменение
        change_permission = Permission.objects.create(
            codename=f'change_ordersbot_{instance.city}',
            name=f'Can change OrdersBot {instance.city}',
            content_type=content_type
        )


@receiver(post_delete, sender=OrdersBot)
def delete_orders_bot_permissions(sender, instance, **kwargs):
    # Удаляем пермишены, связанные с этим объектом
    Permission.objects.filter(
        codename=f'change_ordersbot_{instance.city}').delete()
