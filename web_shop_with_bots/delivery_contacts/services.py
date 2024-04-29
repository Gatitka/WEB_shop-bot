from decimal import Decimal

from django.conf import settings

from delivery_contacts.models import Delivery, DeliveryZone

from .utils import (_get_delivery_zone, get_delivery_cost,
                    google_validate_address_and_get_coordinates)


import logging

# Создаем логгер
logger = logging.getLogger(__name__)

def get_delivery(request, type):
    city = request.data.get('city', settings.DEFAULT_CITY)
    if city is None:
        city = settings.DEFAULT_CITY

    delivery = Delivery.objects.filter(
        city=city,
        type=type,
        is_active=True
    ).first()

    return delivery


def get_delivery_zone(city, lat=None, lon=None):
    """
    Функция возвращает зону доставки по адресу или координатам.
    """
    delivery_zones = DeliveryZone.objects.filter(city=city)
    delivery_zone = _get_delivery_zone(delivery_zones, lat, lon)
    if delivery_zone is None:
        return DeliveryZone.objects.get(name="уточнить", city=city)
    return delivery_zone


def get_delivery_cost_zone(city, amount, delivery,
                           lat, lon, free_delivery=False):
    """
    Рассчитывает стоимость доставки и зону с учетом суммы заказа и адреса доставки.
    """
    # Перебираем все районы доставки и проверяем, входит ли адрес в каждый из них
    # if lat is None and lon is None:
    #     lat, lon, status = google_validate_address_and_get_coordinates(address)
    delivery_zone = get_delivery_zone(city,
                                      lat, lon)

    if not free_delivery:
        delivery_cost = get_delivery_cost(amount, delivery,
                                          delivery_zone)
    else:
        delivery_cost = Decimal(0)

    return delivery_cost, delivery_zone


def get_delivery_cost_zone_by_address(city, discounted_amount, delivery,
                                      address):
    """
    Рассчитывает стоимость доставки и зону с учетом суммы заказа и адреса доставки.
    """
    # Перебираем все районы доставки и проверяем, входит ли адрес в каждый из них
    lat, lon, status = google_validate_address_and_get_coordinates(address)
    logger.warning(f'получение координат из адреса, через бэк {address}')
    delivery_zone = get_delivery_zone(city,
                                      lat, lon)

    delivery_cost = get_delivery_cost(discounted_amount, delivery,
                                      delivery_zone)

    return delivery_cost, delivery_zone
