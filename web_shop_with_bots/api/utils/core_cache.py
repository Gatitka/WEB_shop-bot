from django.core.cache import cache


CONTACTS_DELIVERY_CACHE_KEY = "contacts_delivery"
DELIVERY_ZONES_CACHE_KEY = "delivery_zones"
PROMONEWS_CACHE_KEY = "promonews"
BANNERS_CACHE_KEY = "banners"
TAKEAWAY_CONDITIONS_CACHE_KEY = "create_order_takeaway_conditions"
DELIVERY_CONDITIONS_CACHE_KEY = "create_order_delivery_conditions"

MENU_CACHE_KEYS = [
    "menu_/api/v1/menu/",
]


def invalidate_menu_cache():
    cache.delete_many(
        MENU_CACHE_KEYS
    )


def invalidate_contacts_cache():
    cache.delete_many([
        CONTACTS_DELIVERY_CACHE_KEY,
        TAKEAWAY_CONDITIONS_CACHE_KEY,
        DELIVERY_CONDITIONS_CACHE_KEY,
    ])


def invalidate_delivery_zones_cache():
    cache.delete(DELIVERY_ZONES_CACHE_KEY)


def invalidate_promonews_cache():
    cache.delete(PROMONEWS_CACHE_KEY)


def invalidate_banners_cache():
    cache.delete(BANNERS_CACHE_KEY)

def invalidate_orders_conditions_cache():
    cache.delete_many([
        DELIVERY_CONDITIONS_CACHE_KEY,
        TAKEAWAY_CONDITIONS_CACHE_KEY,
    ])

def invalidate_cache_for_model(model):
    """ Тригерится, когда изменения модели через Actions."""
    from catalog.models import (Dish, Category, DishCategory,
                                DishCityPrice, DishPartnerPrice)
    from delivery_contacts.models import Restaurant, Delivery, DeliveryZone
    from tm_bot.models import OrdersBot
    from promos.models import Banner, PromoNews

    if model in [Dish, Category, DishCategory, DishCityPrice, DishPartnerPrice]:
        invalidate_menu_cache()
        invalidate_orders_conditions_cache()
        invalidate_banners_cache()

    elif model in [Restaurant, Delivery, OrdersBot]:
        invalidate_contacts_cache()

    elif model == DeliveryZone:
        invalidate_delivery_zones_cache()

    elif model == Banner:
        invalidate_banners_cache()

    elif model == PromoNews:
        invalidate_promonews_cache()

    # CityDishList , RestaurantDishList не описаны,
    # тк нет активации в actions
