from datetime import date

from django.db.models import Max
from django.db.models.signals import pre_delete, post_delete, pre_save, post_save
from django.contrib.auth.models import Permission, ContentType
from django.dispatch import receiver

from .models import Dish, CityDishList, RestaurantDishList


@receiver(pre_save, sender=Dish)
def reset_order_number(sender, instance, **kwargs):
    if instance.pk is None:  # Проверяем, что это новый заказ
        max_dish_id = Dish.objects.filter(
            category=instance.category
        ).aggregate(Max('dish_id'))['dish_id__max'] or 0
        # Устанавливаем номер заказа на единицу больше MAX текущей даты
        instance.id = max_dish_id + 1


@receiver(post_save, sender=CityDishList)
def create_citydishlist_permissions(sender, instance, created, **kwargs):
    if created:
        content_type = ContentType.objects.get_for_model(CityDishList)

        # Создаем разрешение на изменение
        change_permission = Permission.objects.create(
            codename=f'change_citydishlist_{instance.city}',
            name=f'Can change CityDishList {instance.city}',
            content_type=content_type
        )


@receiver(post_delete, sender=CityDishList)
def delete_restaurant_permissions(sender, instance, **kwargs):
    # Удаляем пермишены, связанные с этим объектом
    Permission.objects.filter(
        codename=f'change_citydishlist_{instance.city}').delete()


@receiver(post_save, sender=RestaurantDishList)
def create_citydishlist_permissions(sender, instance, created, **kwargs):
    if created:
        content_type = ContentType.objects.get_for_model(RestaurantDishList)

        # Создаем разрешение на изменение
        change_permission = Permission.objects.create(
            codename=f'change_restdishlist_{instance.restaurant_id}',
            name=f'Can change RestaurantDishList {instance.restaurant_id}',
            content_type=content_type
        )


@receiver(post_delete, sender=RestaurantDishList)
def delete_restaurant_permissions(sender, instance, **kwargs):
    # Удаляем пермишены, связанные с этим объектом
    Permission.objects.filter(
        codename=f'change_restdishlist_{instance.restaurant_id}').delete()
