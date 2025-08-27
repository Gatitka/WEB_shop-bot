from datetime import date

from django.db.models import Max
from django.db.models.signals import pre_delete, post_delete, pre_save, post_save, m2m_changed
from django.contrib.auth.models import Permission, ContentType
from django.dispatch import receiver

from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Dish, Category, CityDishList, RestaurantDishList


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


@receiver(m2m_changed, sender=Dish.category.through)
def handle_category_priority(sender, instance, action, reverse, pk_set, **kwargs):
    if reverse or action not in ['post_add', 'post_remove', 'post_clear']:
        return

    # ========== ДОБАВЛЕНА КАТЕГОРИЯ ==========
    if action == 'post_add':
        if not pk_set:
            return

        # Возьмём первую добавленную категорию (возможна адаптация)
        category_pk = list(pk_set)[0]
        try:
            category = Category.objects.get(pk=category_pk)
        except Category.DoesNotExist:
            return

        if instance.priority:
            conflict = Dish.objects.filter(
                category=category,
                priority=instance.priority
            ).exclude(pk=instance.pk).exists()

            if conflict:
                transaction.set_rollback(True)
                raise ValidationError(
                    f"Приоритет {instance.priority} уже занят в категории '{category}'."
                )
            # приоритет допустим, ничего не делаем
        else:
            # приоритет не указан — автоустановка
            max_priority = Dish.objects.filter(
                category=category
            ).aggregate(Max('priority'))['priority__max'] or 0

            instance.priority = max_priority + 1
            instance.save()

    # ========== УДАЛЕНА КАТЕГОРИЯ ==========
    elif action in ['post_remove', 'post_clear']:
        if not instance.category.exists():
            instance.priority = None
            instance.save()
