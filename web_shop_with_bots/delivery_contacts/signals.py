from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import Permission, ContentType
from django.dispatch import receiver
from .models import Restaurant, Delivery, DeliveryZone, Courier


@receiver(post_save, sender=Restaurant)
def create_restaurant_permissions(sender, instance, created, **kwargs):
    if created:
        content_type = ContentType.objects.get_for_model(Restaurant)

        # Создаем разрешение на изменение
        change_permission = Permission.objects.create(
            codename=f'change_restaurant_{instance.pk}',
            name=f'Can change Restaurant {instance.pk}',
            content_type=content_type
        )
        change_rest_ord_permission = Permission.objects.create(
            codename=f'change_orders_rest_{instance.pk}',
            name=f'Can change Restaurant {instance.pk}',
            content_type=content_type
        )


@receiver(post_delete, sender=Restaurant)
def delete_restaurant_permissions(sender, instance, **kwargs):
    # Удаляем пермишены, связанные с этим объектом
    Permission.objects.filter(
        codename=f'change_restaurant_{instance.pk}').delete()
    Permission.objects.filter(
        codename=f'change_orders_rest_{instance.pk}').delete()


@receiver(post_save, sender=Delivery)
def create_delivery_permissions(sender, instance, created, **kwargs):
    if created:
        content_type = ContentType.objects.get_for_model(Delivery)

        # Создаем разрешение на изменение
        change_permission, _ = Permission.objects.get_or_create(
            codename=f'change_delivery_{instance.city}',
            name=f'Can change Delivery {instance.city}',
            content_type=content_type
        )


@receiver(post_delete, sender=Delivery)
def delete_delivery_permissions(sender, instance, **kwargs):
    # Удаляем пермишены, связанные с этим объектом

    if not Delivery.objects.filter(city=instance.city).exists():
        Permission.objects.filter(
            codename=f'change_delivery_{instance.city}').delete()


@receiver(post_save, sender=DeliveryZone)
def create_delivery_zone_permissions(sender, instance, created, **kwargs):
    if created:
        content_type = ContentType.objects.get_for_model(DeliveryZone)

        # Создаем разрешение на изменение
        change_permission, _ = Permission.objects.get_or_create(
            codename=f'change_delivery_zone_{instance.city}',
            name=f'Can change DeliveryZone {instance.city}',
            content_type=content_type
        )


@receiver(post_delete, sender=DeliveryZone)
def delete_delivery_zone_permissions(sender, instance, **kwargs):
    # Удаляем пермишены, связанные с этим объектом
    if not DeliveryZone.objects.filter(city=instance.city).exists():
        Permission.objects.filter(
            codename=f'change_delivery_zone_{instance.city}').delete()


@receiver(post_save, sender=Courier)
def create_courier_permissions(sender, instance, created, **kwargs):
    if created:
        content_type = ContentType.objects.get_for_model(Courier)

        # Создаем разрешение на изменение
        change_permission = Permission.objects.create(
            codename=f'change_courier_{instance.city}',
            name=f'Can change Courier {instance.city}',
            content_type=content_type
        )


@receiver(post_delete, sender=Courier)
def delete_courier_permissions(sender, instance, **kwargs):
    # Удаляем пермишены, связанные с этим объектом
    Permission.objects.filter(
        codename=f'change_courier_{instance.city}').delete()
