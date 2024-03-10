from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import datetime, time, timezone


def validate_delivery_time(value, delivery, restaurant=None):
    if value is not None:

        if value <= datetime.now(value.tzinfo):
            raise ValidationError("Delivery time can't be in the past.")

        if delivery is None:
            raise ValidationError(
                    'Delivery method is not chosen.'
                )
        # Проверяем, что время находится в диапазоне
        # работы доставки в модели доставки
        if delivery.type == 'delivery':
            delivery_time = value.time()
            min_time = delivery.min_time
            max_time = delivery.max_time

            if not min_time <= delivery_time <= max_time:
                min_time_str = min_time.strftime('%H:%M')
                max_time_str = max_time.strftime('%H:%M')

                raise ValidationError(
                    (f'Choose time '
                     f"Choose time {min_time_str} - {max_time_str}"),
                    code='invalid_order_time'
                )

        elif delivery.type == 'takeaway':
            delivery_time = value.time()
            if restaurant is not None:
                min_time = restaurant.open_time
                max_time = restaurant.close_time
                if not min_time <= delivery_time <= max_time:
                    raise ValidationError(
                        (f'Choose time '
                         f'{str(min_time)} до {str(max_time)}'),

                        code='invalid_delivery_time'
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


def validate_address_w_google(recipient_address):
    if recipient_address is None:
        raise ValidationError(
            "Внесите адрес доставки."
        )


def validate_selected_month(value):
    if value is not None:
        try:
            datetime_obj = datetime.strptime(value, '%d %b')
        except ValueError:
            raise ValidationError(
                "Invalid date format. Date should be in the format 'dd MMM'.",
                code='invalid_date_format'
            )

        now = timezone.now()
        if datetime_obj <= now:
            raise ValidationError(
                "Delivery time cannot be in the past.",
                code='delivery_time_in_past'
            )
    return value


def cart_valiation(cart, half_validation=False):
    validate_cart_is_not_none(cart)
    if not half_validation:
        validate_cartdishes_exist(cart)


def validate_cart_is_not_none(cart):
    if cart is None:
        raise ValidationError(
            "Mistake while handling the cart. Try to pick the cart one more time."
        )


def validate_cartdishes_exist(cart):
    if not cart.cartdishes.exists():
        raise ValidationError(
            "Your cart is empty. Please add something into your cart."
        )
