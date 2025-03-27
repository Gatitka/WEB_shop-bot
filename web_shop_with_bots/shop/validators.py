from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from delivery_contacts.models import Restaurant
from delivery_contacts.utils import parse_address_comment
from .utils import (split_and_get_comment,
                    get_delivery_time_if_none)
from datetime import timedelta


def validate_delivery_time(value, delivery, restaurant=None):
    if delivery is None:
        raise ValidationError(
            "No sufficent handling option for takeaway/delivery is found. "
            "Maybe chosen type of delivery is unavailable "
            "or chosen restaurant is closed.")

    if delivery.type == 'delivery':
        min_time = delivery.min_acc_time
        max_time = delivery.max_acc_time
        handoff_min_time = delivery.min_time
        handoff_max_time = delivery.max_time

    if delivery.type == 'takeaway':
        if restaurant is not None:
            if not isinstance(restaurant, Restaurant):
                restaurant = Restaurant.objects.filter(id=restaurant).first()
            if restaurant:
                min_time = restaurant.min_acc_time
                max_time = restaurant.max_acc_time
                handoff_min_time = restaurant.open_time
                handoff_max_time = restaurant.close_time

    if value is None:
        current_localtime = timezone.localtime()
        current_time = current_localtime.time()

        # Проверяем, что время размещения заказа с "сегодня/как можно скорее"
        # находится в диапазоне приема заказов на сегодня.
        if not min_time <= current_time <= max_time:
            min_time_str = handoff_min_time.strftime('%H:%M')
            max_time_str = handoff_max_time.strftime('%H:%M')

            raise ValidationError(
                (f"Worktime {min_time_str}-{max_time_str}"),
                code='invalid_order_time'
            )

    if value is not None:
        if value <= timezone.localtime():
            raise ValidationError(_("Delivery time can't be in the past."))

        two_months_later = timezone.localtime() + timedelta(days=60)
        if value > two_months_later:
            raise ValidationError(_(("Delivery time can't be more "
                                     "than 2 months ahead.")))

        delivery_time = value.time()

        # Проверяем, что выбранное время выдачи находится в диапазоне
        # доступного времени выдачи доставки/самовывоза.
        if not handoff_min_time <= delivery_time <= handoff_max_time:
            min_time_str = handoff_min_time.strftime('%H:%M')
            max_time_str = handoff_max_time.strftime('%H:%M')

            raise ValidationError(
                (f"Worktime {min_time_str}-{max_time_str}"),
                code='invalid_order_time'
            )


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


def validate_user_order_exists(order):
    if order is None:
        # logger.warning("No such order ID in user's history.")
        return ValidationError(_("There's no such order ID in "
                                 "your orders history."))


def validate_flat(form):
    delivery = form.cleaned_data.get('delivery')
    if delivery is not None and delivery.type == 'delivery':
        flat = form.cleaned_data.get('flat')
        if flat in [None, '']:
            return ValidationError(_("Flat can't be empty."))


def validate_payment_type(data):
    if data is None:
        raise ValidationError("Payment type can't be empty.")

    if data not in [method[0] for method in settings.PAYMENT_METHODS]:
        raise ValidationError("Invalid payment type.")


def validate_city(value):
    valid_cities = [city[0] for city in settings.CITY_CHOICES]
    if value not in valid_cities:
        raise ValidationError(
            _("City is incorect."))


def validate_comment(value):
    address_comment, comment = split_and_get_comment(value)
    address_comment_data = parse_address_comment(address_comment)
    for key in address_comment_data.keys():
        if len(address_comment_data[key]) > 100:
            raise ValidationError(f"{key} is over 100 symbols")
    if comment is not None and len(comment) > 1500:
        raise ValidationError("comment is over 1500 symbols")
