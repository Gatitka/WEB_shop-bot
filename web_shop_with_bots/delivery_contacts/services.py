from decimal import Decimal
from django.core.cache import cache
from django.conf import settings
from rest_framework.exceptions import ValidationError

from delivery_contacts.models import Delivery, DeliveryZone

from .utils import (_get_delivery_zone, get_delivery_cost,
                    google_validate_address_and_get_coordinates)


import logging

# Создаем логгер
logger = logging.getLogger(__name__)


RESTAURANT_DELIVERY_ACTIVE_CACHE_PREFIX = "restaurant_delivery_active_"


def is_restaurant_delivery_active(city):
    cache_key = f"{RESTAURANT_DELIVERY_ACTIVE_CACHE_PREFIX}{city}"
    cached = cache.get(cache_key)
    if cached is not None:
        return bool(cached)

    is_active = Delivery.objects.filter(
        city=city, type='restaurant', is_active=True
    ).exists()
    cache.set(cache_key, int(is_active), timeout=24 * 3600)
    return is_active


def is_restaurant_partner(user):
    return (
            user.is_authenticated
            and user.groups.filter(name=settings.RESTAURANT_PARTNER_GROUP).exists()
        )



def get_delivery(request, type):
    """Выбор объекта доставки в засимости от типа заказа.
    Если заказ и Белграда и заказ у партнера """
    city = request.data.get('city', settings.DEFAULT_CITY)
    if city is None:
        city = settings.DEFAULT_CITY

    user = request.user

    if is_restaurant_partner(user) and is_restaurant_delivery_active(city):
        restaurant_delivery = Delivery.objects.filter(
            city=city, type='restaurant', is_active=True
        ).first()
        if restaurant_delivery:
            return restaurant_delivery

    delivery = Delivery.objects.filter(
        city=city,
        type=type,
        is_active=True
    ).first()

    return delivery

# def get_delivery(request, type):
#     city = request.data.get('city', settings.DEFAULT_CITY)
#     if city is None:
#         city = settings.DEFAULT_CITY

#     delivery = Delivery.objects.filter(
#         city=city,
#         type=type,
#         is_active=True
#     ).first()

#     return delivery


def get_delivery_zone(city, lat=None, lon=None):
    """
    Функция возвращает зону доставки по адресу или координатам.
    """
    all_delivery_zones = DeliveryZone.objects.filter(city=city)
    # delivery_zones = all_delivery_zones.exclude(
    #                                     name__in=['уточнить', 'по запросу'])
    delivery_zone = _get_delivery_zone(all_delivery_zones, lat, lon)
    if delivery_zone is None:
        delivery_zone = get_cached_delivery_zone_utochnit()
        # return all_delivery_zones.filter(name='уточнить').first()
    return delivery_zone


def get_delivery_cost_zone(city, amount, delivery,
                           lat, lon, free_delivery=False):
    """
    Рассчитывает стоимость доставки и зону с учетом суммы заказа
    и адреса доставки.
    """
    # Перебираем все районы доставки и проверяем, входит ли адрес
    # в каждый из них
    delivery_zone = get_delivery_zone(city,
                                      lat, lon)

    if not free_delivery:
        delivery_cost = get_delivery_cost(amount, delivery,
                                          delivery_zone)
    else:
        delivery_cost = Decimal(0)

    return delivery_cost, delivery_zone


def get_delivery_cost_zone_by_address(city, amount, delivery,
                                      address):
    """
    Рассчитывает стоимость доставки и зону с учетом суммы заказа и адреса доставки.
    """
    # Перебираем все районы доставки и проверяем, входит ли адрес в каждый из них
    logger.warning(f'получение координат из адреса, через бэк {address, city}')
    lat, lon = google_validate_address_and_get_coordinates(address, city)

    delivery_zone = get_delivery_zone(city,
                                      lat, lon)

    delivery_cost = get_delivery_cost(amount, delivery,
                                      delivery_zone)

    return delivery_cost, delivery_zone


def get_cached_delivery_zone_utochnit():
    cache_key = f"delivery_zone_utochnit"
    delivery_zone = cache.get_or_set(
        cache_key,
        lambda: DeliveryZone.objects.filter(name='уточнить').first(),
        timeout=24*3600)  # Таймаут: 1 час (3600 секунд)
    return delivery_zone
