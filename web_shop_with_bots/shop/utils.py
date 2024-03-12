from users.models import BaseProfile
from rest_framework import status
from rest_framework.response import Response
from datetime import date, datetime, timedelta
from django.db.models import Max
from django.core.exceptions import ValidationError
from rest_framework import serializers
from django.shortcuts import get_object_or_404
from delivery_contacts.models import Delivery
from decimal import Decimal
from .validators import cart_valiation
from delivery_contacts.services import get_delivery_cost_zone


def get_base_profile_w_cart(current_user):
    return BaseProfile.objects.filter(
        web_account=current_user
    ).select_related(
        'shopping_cart',
        'shopping_cart__promocode'
    ).prefetch_related(
        'shopping_cart__cartdishes'
    ).first()


def get_cart_base_profile(base_profile, validation=True, half_validation=False):
    cart = base_profile.shopping_cart
    if validation:
        cart_valiation(cart, half_validation)

    return cart


def get_cart(current_user, validation=True, half_validation=False):
    base_profile = get_base_profile_w_cart(current_user)
    if base_profile:
        return get_cart_base_profile(base_profile, validation, half_validation)
    return None


def get_base_profile_and_shopping_cart(current_user, validation=True,
                                       half_validation=False):
    base_profile = get_base_profile_w_cart(current_user)
    cart = None
    if base_profile:
        cart = get_cart_base_profile(base_profile, validation, half_validation)
    return base_profile, cart


def get_base_profile_cartdishes_promocode(current_user, validation=True,
                                          half_validation=False):
    base_profile, cart = get_base_profile_and_shopping_cart(current_user,
                                                            validation,
                                                            half_validation)
    if base_profile and cart:
        cartdishes = cart.cartdishes.all()
        promocode = cart.promocode

        return base_profile, cart, cartdishes, promocode


def get_next_item_id_today(model, field):
    today_start = datetime.combine(date.today(), datetime.min.time())  # Начало текущего дня
    today_end = today_start + timedelta(days=1) - timedelta(microseconds=1)  # Конец текущего дня

    max_id = model.objects.filter(
        created__range=(today_start, today_end)
    ).aggregate(Max(field))[f'{field}__max']
    # Устанавливаем номер заказа на единицу больше MAX текущей даты
    if max_id is None:
        return 1
    else:
        return max_id + 1


def get_reply_data_delivery(delivery, city, lat, lon,
                            cart=None,
                            orderdishes=None, promocode=None):

    amount = get_amount(cart, orderdishes)

    promocode, promocode_discount, discounted_amount = (
        get_promocode_promoc_disc_disc_amount(amount, cart, promocode)
    )

    delivery_discount = get_delivery_discount(delivery,
                                              discounted_amount)

    total_discount = Decimal(
        promocode_discount + delivery_discount).quantize(Decimal('0.01'))

    delivery_cost, delivery_zone = get_delivery_cost_zone(
                city, discounted_amount, delivery, lat, lon)

    reply_data = get_rep_dic_delivery(amount, promocode, total_discount,
                                      delivery, delivery_zone, delivery_cost,
                                      discounted_amount, delivery_discount)
    # total посчитается и оформится внутри

    return reply_data


def get_rep_dic_delivery(amount, promocode, total_discount,
                         delivery, delivery_zone, delivery_cost,
                         discounted_amount, delivery_discount):
    reply_data = {
        'amount': amount,
        'promocode': promocode,
        'total_discount': total_discount
    }

    reply_data = get_rep_dic(reply_data,
                             delivery, delivery_zone,
                             discounted_amount, delivery_discount,
                             delivery_cost)

    return reply_data


def get_rep_dic(reply_data,
                delivery=None, delivery_zone=None,
                discounted_amount=None, delivery_discount=None,
                delivery_cost=None,
                instance=None):

    if instance:
        delivery = instance.delivery
        delivery_zone = instance.delivery_zone

    if (delivery.type == 'delivery'
       and delivery_zone.name == 'уточнить'):

        if instance is None:
            total = (
                Decimal(discounted_amount) - Decimal(delivery_discount)
            )
        else:
            total = instance.discounted_amount

        reply_data['delivery_cost'] = "Requires clarification"
        reply_data['process_comment'] = (
            "Delivery address is outside our service area or "
            "an error occurred while processing the delivery data."
            "Please check with the administrator regarding "
            "the delivery possibility and it's cost."
        )

        reply_data['total'] = {
            "title": "Total amount, excl. delivery",
            "total_amount": total
            }

    else:
        if instance is None:
            total = (
                Decimal(discounted_amount) - Decimal(delivery_discount) +
                Decimal(delivery_cost)
            )

            reply_data['delivery_cost'] = delivery_cost

        else:
            total = instance.final_amount_with_shipping
            reply_data['delivery_cost'] = instance.delivery_cost

        reply_data['total'] = {
                "title": "Total amount, incl. delivery",
                "total_amount": total
                }

    return reply_data


def get_amount(cart=None, orderdishes=None):
    if cart:
        return cart.amount

    if orderdishes:
        amount = Decimal(0)
        for orderdish in orderdishes:
            dish = orderdish['dish']
            amount += Decimal(dish.final_price * orderdish['quantity'])
        return amount


def get_promocode_promoc_disc_disc_amount(amount, cart=None, promocode=None):
    if cart:
        if cart.promocode is None:
            promocode_code = None
            promocode_discount = Decimal(0)
            discounted_amount = amount

        else:
            promocode_code = cart.promocode.promocode
            promocode_discount = cart.discount
            discounted_amount = cart.discounted_amount
        return promocode_code, promocode_discount, discounted_amount

    else:
        #  для незареганых пользователей
        if promocode is None:
            promocode_code = None
            promocode_discount = Decimal(0)
            discounted_amount = amount
        else:
            promocode_code = promocode.promocode
            promocode_discount = Decimal(
                amount * promocode.discount / Decimal(100)
            ).quantize(Decimal('0.01'))
            discounted_amount = Decimal(
                (amount - promocode_discount).quantize(Decimal('0.01'))
            )

        return promocode_code, promocode_discount, discounted_amount


def get_delivery_discount(delivery, discounted_amount):
    if delivery.discount:
        delivery_discount = (
            Decimal(discounted_amount)
            * Decimal(delivery.discount) / Decimal(100)
        ).quantize(Decimal('0.01'))
    else:
        delivery_discount = Decimal(0)
    return delivery_discount


def get_reply_data_takeaway(delivery,
                            cart=None,
                            orderdishes=None, promocode=None, ):

    amount = get_amount(cart, orderdishes)

    promocode, promocode_discount, discounted_amount = (
        get_promocode_promoc_disc_disc_amount(amount, cart, promocode)
    )
    delivery_discount = get_delivery_discount(delivery,
                                              discounted_amount)

    total_discount = Decimal(
        promocode_discount + delivery_discount).quantize(Decimal('0.01'))

    total = Decimal(
        discounted_amount - delivery_discount).quantize(Decimal('0.01'))

    reply_data = get_rep_dic_takeaway(amount, promocode, total_discount, total)

    return reply_data


def get_rep_dic_takeaway(amount, promocode, total_discount, total):
    reply_data = {
        'amount': amount,
        'promocode': promocode,
        'total_discount': total_discount,
        'total': {
            "title": "Total amount",
            "total_amount": total
            }
    }
    return reply_data


def get_repeat_order_form_data(order):
    repeat_order_form_data = {
        "recipient_name": order.recipient_name,
        "recipient_phone": str(order.recipient_phone),
        "city": order.city,
        "comment": order.comment,
        "persons_qty": order.persons_qty,
        "delivery": str(order.delivery.type),
    }

    if order.delivery.type == 'delivery':
        repeat_order_form_data['recipient_address'] = order.recipient_address
        repeat_order_form_data['delivery_zone'] = str(order.delivery_zone)

    elif order.delivery.type == 'takeaway':
        repeat_order_form_data['restaurant'] = order.restaurant

    return repeat_order_form_data


def get_first_item_true(obj):
    # Преобразование поля datetime в строку с помощью strftime()
    model_class = obj.__class__
    if obj.user is not None:
        if not model_class.objects.filter(user=obj.user).exists():
            return True
    else:
        if not model_class.objects.filter(
            recipient_phone=obj.recipient_phone
        ).exists():
            return True
    return False
