from datetime import datetime, time, timezone

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from delivery_contacts.models import Restaurant


def validate_delivery_time(value, delivery, restaurant=None):
    if value is not None:

        if value <= datetime.now(value.tzinfo):
            raise ValidationError(_("Delivery time can't be in the past."))

        if delivery is None:
            raise ValidationError(
                    _("Delivery method is required for "
                      "delivery time validation.")
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
                    (_(f"Choose time {min_time_str} - {max_time_str}")),
                    code='invalid_order_time'
                )

        elif delivery.type == 'takeaway':
            delivery_time = value.time()
            if restaurant is not None:
                restaurant = Restaurant.objects.filter(id=restaurant).first()
                if restaurant:
                    min_time = restaurant.open_time
                    max_time = restaurant.close_time

                    if not min_time <= delivery_time <= max_time:
                        min_time_str = min_time.strftime('%H:%M')
                        max_time_str = max_time.strftime('%H:%M')
                        raise ValidationError(
                            (f'Choose time '
                             f'{min_time_str} - {max_time_str}'),

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
            {"restaurant": _("Please, choose the restaurant.")}
        )


def validate_address(recipient_address):
    if recipient_address is None:
        raise ValidationError(
            {"recipient_address": _("Please, enter the delivery address.")}
        )


def validate_address_w_google(recipient_address):
    if recipient_address is None:
        raise ValidationError(
            _("Please, enter the delivery address.")
        )


def cart_valiation(cart, half_validation=False):
    validate_cart_is_not_none(cart)
    if not half_validation:
        validate_cartdishes_exist(cart)


def validate_cart_is_not_none(cart):
    if cart is None:
        raise ValidationError(
            _("Mistake while handling the cart. "
              "Try to pick the cart one more time.")
        )


def validate_cartdishes_exist(cart):
    if not cart.cartdishes.exists():
        raise ValidationError(
            _("Your cart is empty. Please add something into your cart.")
        )
