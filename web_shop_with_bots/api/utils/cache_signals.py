"""
cache_signals.py — это файл, который автоматически сбрасывает API-кэш, когда в админке или коде меняются связанные модели.

Как он работает по сути
Подписывается на Django-сигналы:
post_save — объект сохранили
post_delete — объект удалили
m2m_changed — поменяли many-to-many связь
Слушает нужные модели — например:
Dish, Category, DishCategory → меню
Restaurant, Delivery, OrdersBot → контакты/условия заказа
DeliveryZone → зоны доставки
Banner → баннеры
PromoNews → новости/баннеры
CityDishList, RestaurantDishList → условия заказа/баннеры
Когда что-то меняется — вызывает нужную функцию очистки кэша из core_cache.py, например:
invalidate_menu_cache()
invalidate_contacts_cache()
invalidate_banners_cache() и т.д.
На примере

Если сохранили Dish, срабатывает этот receiver:

@receiver([post_save, post_delete], sender=Dish)
@receiver([post_save, post_delete], sender=Category)
@receiver([post_save, post_delete], sender=DishCategory)
def invalidate_menu_related_cache(...):
    invalidate_menu_cache()
    invalidate_orders_conditions_cache()
    invalidate_banners_cache()

То есть после изменения блюда файл говорит примерно так:
«меню, условия заказа и баннеры могли устареть — удаляем их из кэша»."""

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

from catalog.models import (Dish, Category, DishCategory,
                            CityDishList, RestaurantDishList,
                            DishCityPrice, DishPartnerPrice)
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


@receiver([post_save, post_delete], sender=DishCityPrice)
@receiver([post_save, post_delete], sender=DishPartnerPrice)
def invalidate_menu_cache_on_price_change(sender, instance, **kwargs):
    """
    Изменения городских цен блюда влияют на:
    - menu
    - menu2
    """
    invalidate_menu_cache()

    logger.warning(
        "MENU CACHE INVALIDATED BY PRICE CHANGE: %s %s",
        sender,
        instance,
    )
