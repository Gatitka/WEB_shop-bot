from datetime import datetime
from decimal import Decimal

import requests
from django.conf import settings
from django.core.exceptions import ValidationError

from web_shop_with_bots.settings import GOOGLE_API_KEY

import logging
# Создаем логгер
logger = logging.getLogger(__name__)

def receive_responce_from_google(address, city):
    logger.debug(f"Запрос координат для адреса: '{address}', город: '{city}'")

    final_address = check_address_contains_city(address, city)
    logger.debug(f"Итоговый адрес для запроса: '{final_address}'")

    # Базовые параметры
    params = {
        'key': GOOGLE_API_KEY,
        'address': final_address,
        'region': 'rs',
    }

    # Добавляем компонентную фильтрацию, если город указан
    if city:
        # Формат для компонентной фильтрации: "component:value|component:value"
        # Для города используем тип "locality"
        params['components'] = f'locality:{city}|country:rs'

    base_url = 'https://maps.googleapis.com/maps/api/geocode/json?'
    logger.debug(f"Отправка запроса к Google API с параметрами: {params}")

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        logger.debug(f"Получен ответ от Google API: статус '{data.get('status')}', response: {data}")
        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к API Google Maps: {e}")
        return None


def google_validate_address_and_get_coordinates(address, city=None):
    logger.info(f"Запрос на проверку и получение координат для адреса: '{address}', город: '{city}'")

    data = receive_responce_from_google(address, city)

    # Проверяем, получили ли мы вообще данные
    if not data:
        logger.error(f"Не получен ответ от сервиса геокодирования для адреса: '{address}', город: '{city}'")
        raise ValidationError('Нет ответа от сервиса геокодирования. Проверьте подключение.')

    # Проверяем успешность запроса
    if data['status'] != 'OK':
        error_message = {
            'ZERO_RESULTS': 'Адрес не найден',
            'OVER_QUERY_LIMIT': 'Превышен лимит запросов к API',
            'REQUEST_DENIED': 'Запрос отклонен сервисом',
            'INVALID_REQUEST': 'Неверный формат запроса',
            'UNKNOWN_ERROR': 'Неизвестная ошибка сервиса геокодирования'
        }.get(data['status'], f'Ошибка геокодирования: {data["status"]}')

        logger.info(f"Ошибка геокодирования: {data['status']} для адреса: '{address}', город: '{city}'")
        raise ValidationError(f'{error_message}. Проверьте точность адреса доставки.')

    # Если результаты есть
    if data['results']:
        location_type = data['results'][0]['geometry']['location_type']
        logger.info(f"Найден результат с точностью: {location_type} для адреса: '{address}'")

        # но не с точностью ROOFTOP
        if location_type not in ['ROOFTOP', 'RANGE_INTERPOLATED']:
            logger.info(f"Недостаточная точность ({location_type}) для адреса: '{address}', город: '{city}'")
            raise ValidationError(
                'Невозможно точно определить координаты адреса. Проверьте точность адреса доставки.'
            )
    else:
        logger.info(f"Получен пустой список результатов для адреса: '{address}', город: '{city}'")
        raise ValidationError('Не найдены результаты для указанного адреса')

    # Если все проверки пройдены, возвращаем координаты
    geometry = data['results'][0]['geometry']
    lat = geometry['location']['lat']
    lon = geometry['location']['lng']

    logger.info(f"Успешно получены координаты: lat={lat}, lon={lon} для адреса: '{address}, {city}'")
    return lat, lon


def check_address_contains_city(address, city):
    keywords = ["Белград", "Belgrade", "Београд", "Beograd",
                "Novi Sad", "Нови Сад", "Нови Сад", "Novi Sad",
                "Novi-Sad", "Нови-Сад", "Нови-Сад", "Novi-Sad",
                "NoviSad", "НовиСад", "НовиСад", "NoviSad",]

    # Приводим адрес к нижнему регистру для корректной проверки
    address_lower = address.lower() if address else ''

    # Проверяем, содержится ли хотя бы одно из ключевых слов в адресе
    if any(keyword.lower() in address_lower for keyword in keywords):
        return address
    return f"{address}, {city}"

# def get_delivery_cost_zone(delivery_zones, discounted_amount, delivery,
#                            lat, lon):
#     """
#     Рассчитывает стоимость доставки и зону с учетом суммы заказа и адреса доставки.
#     """
#     # Перебираем все районы доставки и проверяем, входит ли адрес в каждый из них
#     # if lat is None and lon is None:
#     #     lat, lon, status = google_validate_address_and_get_coordinates(address)

#     delivery_zone = get_delivery_zone(delivery_zones,
#                                       lat, lon)

#     delivery_cost = get_delivery_cost(discounted_amount, delivery,
#                                       delivery_zone)

#     return delivery_cost, delivery_zone


def _get_delivery_zone(delivery_zones, lat=None, lon=None):
    """
    Функция возвращает зону доставки по адресу или координатам.
    """
    delivery_zone = None

    if lat is not None and lon is not None:
        for zone in delivery_zones:
            if zone.is_point_inside(lat, lon):
                delivery_zone = zone

    return delivery_zone


def get_delivery_cost(amount, delivery, delivery_zone,
                      delivery_cost=None, free_delivery=None):
    """
    Рассчитывает стоимость доставки с учетом суммы заказа и зоны доставки.
    """
    # Перебираем все районы доставки и проверяем, входит ли адрес в каждый из них
    if delivery_zone.name not in ['уточнить', 'по запросу']:

        if free_delivery is True:
            return Decimal(0)

        elif delivery_zone.is_promo and amount >= delivery_zone.promo_min_order_amount:
            # Если для района установлена промо-акция и сумма заказа больше
            # или равна минимальной сумме для промо-акции, доставка бесплатная
            return Decimal(0)
        else:
            # Если промо-акция не действует или сумма заказа меньше минимальной,
            # возвращаем стоимость доставки для данного района
            return delivery_zone.delivery_cost

    elif delivery_zone.name == 'по запросу':
        return Decimal(delivery_cost)

    else:
        if delivery.default_delivery_cost:
            # Если адрес не входит ни в один из районов доставки, возвращаем стоимость доставки
            # по умолчанию (например, стандартная стоимость для города)
            return delivery.default_delivery_cost

        return Decimal(0)


def combine_date_and_time(date_str, time_str):

    if date_str is None and time_str is None:
        return None

    if date_str is not None and time_str is None:
        return None
        #error с фронта не получено время


    # Получаем текущую дату
    current_date = datetime.now()

    # Преобразуем строку даты в объект datetime
    date = datetime.strptime(date_str, "%d.%m")

    # Определяем год для объединения
    if current_date.month == 12 and date.month in [1, 2]:
        # Если текущий месяц - декабрь, а дата - январь, то следующий год
        year = current_date.year + 1
    else:
        # Иначе оставляем текущий год
        year = current_date.year

    # Преобразуем строку времени в объект datetime
    time = datetime.strptime(time_str, "%H:%M").time()

    # Комбинируем дату и время в один объект datetime
    combined_datetime = datetime(year, date.month, date.day, time.hour, time.minute)

    # Преобразуем объединенную дату и время обратно в строку
    # combined_datetime_str = combined_datetime.strftime("%d.%m.%Y %H:%M")

    return combined_datetime


def get_google_api_key():
    return settings.GOOGLE_API_KEY


def parce_coordinates(coordinates):
    latitude, longitude = None, None
    if coordinates:
        parts = coordinates.split(', ')
        latitude = parts[0]
        longitude = parts[1]

        if latitude != 'None' and longitude != 'None':
            latitude, longitude = float(latitude), float(longitude)
            return latitude, longitude

        latitude, longitude = None, None

    return latitude, longitude


def get_address_comment(address):
    flat = address.flat if address.flat is not None else ''
    floor = address.floor if address.floor is not None else ''
    interfon = address.interfon if address.interfon is not None else ''
    return f"flat: {flat}, floor: {floor}, interfon: {interfon}"


import re

def parse_address_comment(address_comment):
    """
    Функция для парсинга строки формата 'flat: 100, floor: 5, interfon: fggftfhj'.
    Поддерживает неполные данные.
    """
    if address_comment is None:
        return {
            'flat': '',
            'floor': '',
            'interfon': ''
        }

    # Определяем шаблон регулярного выражения для парсинга строки
    pattern = re.compile(r'(flat:\s*([^,]+))?|'
                         r'(floor:\s*([^,]+))?|'
                         r'(interfon:\s*([^,]+))?')

    # Ищем все совпадения в строке
    matches = pattern.findall(address_comment)

    # Подготавливаем словарь с пустыми значениями
    result = {
        'flat': '',
        'floor': '',
        'interfon': ''
    }

    # Обрабатываем найденные совпадения
    for match in matches:
        if match[1]:  # если найдено значение flat
            result['flat'] = match[1].strip()
        elif match[3]:  # если найдено значение floor
            result['floor'] = match[3].strip()
        elif match[5]:  # если найдено значение interfon
            result['interfon'] = match[5].strip()

    return result


def get_translate_address_comment(address_comment):
    parsed_data = parse_address_comment(address_comment)
    if parsed_data:
        return (f"кв\\: {parsed_data['flat']}, "
                f"этаж\\: {parsed_data['floor']}, "
                f"интерфон\\: {parsed_data['interfon']}")

    return address_comment
