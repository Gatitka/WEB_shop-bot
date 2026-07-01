import logging

from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver

from api.utils.core_cache import (
    invalidate_menu_cache,
    invalidate_contacts_cache,
    invalidate_delivery_zones_cache,
    invalidate_banners_cache,
    invalidate_promonews_cache,
    invalidate_orders_conditions_cache
)

from catalog.models import Dish, Category, DishCategory, CityDishList, RestaurantDishList
from delivery_contacts.models import Restaurant, Delivery, DeliveryZone
from tm_bot.models import OrdersBot
from promos.models import Banner, PromoNews


logger = logging.getLogger(__name__)


@receiver([post_save, post_delete], sender=Dish)
@receiver([post_save, post_delete], sender=Category)
@receiver([post_save, post_delete], sender=DishCategory)
def invalidate_menu_related_cache(sender, instance, **kwargs):
    """
    Изменения меню влияют на:
    - menu
    - menu2
    - banners
    - create_order_takeaway
    - create_order_delivery
    """
    invalidate_menu_cache()
    invalidate_orders_conditions_cache()
    invalidate_banners_cache()

    logger.warning(
        "MENU/ORDER CONDITIONS CACHE INVALIDATED: %s %s",
        sender,
        instance
    )


@receiver(m2m_changed, sender=Dish.category.through)
def invalidate_menu_categories_cache(sender, instance, **kwargs):
    """
    Изменения связей Dish <-> Category
    """
    invalidate_menu_cache()

    logger.warning(
        "MENU M2M/ORDER CONDITIONS CACHE INVALIDATED: %s %s",
        sender,
        instance
    )


@receiver([post_save, post_delete], sender=Restaurant)
@receiver([post_save, post_delete], sender=Delivery)
@receiver([post_save, post_delete], sender=OrdersBot)
def invalidate_contacts_related_cache(sender, instance, **kwargs):
    """
    Изменения контактов/доставки
    """
    invalidate_contacts_cache()
    invalidate_orders_conditions_cache()

    logger.warning(
        "CONTACTS CACHE INVALIDATED: %s %s",
        sender,
        instance
    )


@receiver([post_save, post_delete], sender=DeliveryZone)
def invalidate_delivery_zones_related_cache(sender, instance, **kwargs):
    """
    Изменения зон доставки
    """
    invalidate_delivery_zones_cache()

    logger.warning(
        "DELIVERY ZONES CACHE INVALIDATED: %s %s",
        sender,
        instance
    )


@receiver([post_save, post_delete], sender=Banner)
def invalidate_banners_related_cache(sender, instance, **kwargs):
    """
    Изменения баннеров
    """
    invalidate_banners_cache()

    logger.warning(
        "BANNERS CACHE INVALIDATED: %s %s",
        sender,
        instance
    )


@receiver([post_save, post_delete], sender=PromoNews)
def invalidate_promonews_related_cache(sender, instance, **kwargs):
    """
    Изменения promo news
    """
    invalidate_promonews_cache()
    invalidate_banners_cache()

    logger.warning(
        "PROMONEWS CACHE INVALIDATED: %s %s",
        sender,
        instance
    )


@receiver([post_save, post_delete], sender=CityDishList)
@receiver([post_save, post_delete], sender=RestaurantDishList)
def invalidate_orders_conditions_lists_cache(sender, instance, **kwargs):
    invalidate_orders_conditions_cache()
    invalidate_banners_cache()

    logger.warning(
        "ORDER CONDITIONS CACHE INVALIDATED BY LIST MODEL: %s %s",
        sender,
        instance
    )


@receiver(m2m_changed, sender=CityDishList.dish.through)
@receiver(m2m_changed, sender=RestaurantDishList.dish.through)
def invalidate_orders_conditions_lists_m2m_cache(sender, instance, **kwargs):
    invalidate_orders_conditions_cache()
    invalidate_banners_cache()

    logger.warning(
        "ORDER CONDITIONS CACHE INVALIDATED BY LIST M2M: %s %s",
        sender,
        instance
    )
