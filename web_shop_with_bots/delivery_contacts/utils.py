from web_shop_with_bots.settings import GOOGLE_API_KEY
import requests
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime


def receive_responce_from_google(address):
    params = {
        'key': GOOGLE_API_KEY,
        'address': address
    }

    base_url = 'https://maps.googleapis.com/maps/api/geocode/json?'

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Проверяем успешность запроса
        data = response.json()  # Парсим ответ в формате JSON
        return data

    except requests.exceptions.RequestException as e:
        # Если произошла ошибка при выполнении запроса, возвращаем None
        print(f'Ошибка при запросе к API Google Maps: {e}')
        return None


def google_validate_address_and_get_coordinates(address):
    data = receive_responce_from_google(address)
    try:
        if data['status'] == 'OK':
            geometry = data['results'][0]['geometry']
            lat = geometry['location']['lat']
            lon = geometry['location']['lng']
            return lat, lon, data['status']
        else:
            # Если статус ответа не 'OK', выбрасываем исключение с сообщением об ошибке
            # raise Exception(f'Ошибка получения координат:'
            #                 f'{data["status"]}, {address}')
            raise ValidationError(
                ('Ошибка получения координат из адреса. '
                 'Проверьте точность адреса доставки.')
            )

    except KeyError as e:
        # # Если произошла ошибка из-за отсутствия ожидаемых ключей в ответе, возвращаем None
        # print(f'Ошибка при разборе ответа от API Google Maps: {e}')
        # return None
        raise ValidationError(
                ('Ошибка получения координат из адреса. '
                 'Проверьте точность адреса доставки.')
            )


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
            if (zone.name in ['zone1', 'zone2', 'zone3']
               and zone.is_point_inside(lat, lon)):

                delivery_zone = zone

    return delivery_zone


def get_delivery_cost(discounted_amount, delivery, delivery_zone, delivery_cost=None):
    """
    Рассчитывает стоимость доставки с учетом суммы заказа и зоны доставки.
    """
    # Перебираем все районы доставки и проверяем, входит ли адрес в каждый из них
    if delivery_zone.name not in ['уточнить', 'по запросу'] :

        if delivery_zone.is_promo and discounted_amount >= delivery_zone.promo_min_order_amount:
            # Если для района установлена промо-акция и сумма заказа больше или равна
            # минимальной сумме для промо-акции, доставка бесплатная
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
