from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import datetime, time, timezone


def validate_order_time(value, delivery, restaurant=None):
    if value is not None:
        if value <= datetime.now(value.tzinfo):
            raise ValidationError(
                'Время доставки не может быть в прошлом.',
                code='delivery_time_in past'
            )

        # Проверяем, что время находится в диапазоне работы доставки в модели доставки
        if delivery.type == 'delivery':
            order_time = value.time()
            min_time = delivery.min_time
            max_time = delivery.max_time
            if not min_time <= order_time <= max_time:
                raise ValidationError(
                    (f'Выберите время в диапозоне '
                     f'{str(min_time)} до {str(max_time)}'),

                    code='invalid_order_time'
                )
        elif delivery.type == 'takeaway':
            order_time = value.time()
            min_time = restaurant.open_time
            max_time = restaurant.close_time
            if not min_time <= order_time <= max_time:
                raise ValidationError(
                    (f'Выберите время в диапозоне '
                     f'{str(min_time)} до {str(max_time)}'),

                    code='invalid_delivery_time'
                )
        else:
            raise ValidationError(
                    'Выберите способ доставки',
                    code='no_delivery_provided'
                )
    else:
        return value

def validate_delivery_data(delivery, restaurant, recipient_address):
    if delivery.type == 'takeaway':
        validate_restaurant(restaurant)
    elif delivery.type == 'delivery':
        validate_address(recipient_address)

def validate_restaurant(restaurant):
    if restaurant is None:
        raise ValidationError(
            {"restaurant": "Выберите ресторан."}
        )

def validate_address(recipient_address):
        if recipient_address is None:
            raise ValidationError(
                {"restaurant": "Внесите адрес доставки."}
            )
