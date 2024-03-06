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


def get_cart(current_user):
    base_profile = get_base_profile_w_cart(current_user)
    if base_profile:
        return get_cart_base_profile(base_profile)
    return None


def get_base_profile_and_shopping_cart(current_user):
    base_profile = get_base_profile_w_cart(current_user)
    cart = None
    if base_profile:
        cart = get_cart_base_profile(base_profile)
    return base_profile, cart


def get_base_profile_w_cart(current_user):
    return BaseProfile.objects.filter(
        web_account=current_user
    ).select_related(
        'shopping_cart',
        'shopping_cart__promocode'
    ).prefetch_related(
        'shopping_cart__cartdishes'
    ).first()


def get_cart_base_profile(base_profile):
    cart = base_profile.shopping_cart

    if cart is None:
        raise serializers.ValidationError(
            "Ошибка при проверке корзины, "
            "попробуйте собрать корзину еще раз."
        )

    if not cart.cartdishes.exists():
        raise serializers.ValidationError(
            "Корзина пуста. Пожалуйста, добавьте блюда в "
            "корзину перед оформлением заказа."
        )

    return cart


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


def get_base_profile_cartdishes_promocode(current_user):
    base_profile, cart = get_base_profile_and_shopping_cart(current_user)
    if base_profile and cart:
        cartdishes = cart.cartdishes.all()
        promocode = cart.promocode

        return base_profile, cart, cartdishes, promocode


def get_reply_data(cart, delivery, delivery_zone=None, delivery_cost=None):
    reply_data = {}

    promocode = cart.promocode
    if cart.promocode is not None:
        promocode = cart.promocode.promocode

    if delivery.discount:
        delivery_discount = (
            Decimal(cart.discounted_amount)
            * Decimal(delivery.discount) / Decimal(100)
        )
    else:
        delivery_discount = Decimal(0)

    if delivery.type == 'delivery' and delivery_zone is None:
        reply_data['delivery_cost'] = "Requires clarification"
        reply_data['comment'] = (
            "Delivery address is outside our service area or "
            "an error occurred while processing the delivery data."
            "Please check with the administrator regarding "
            "the delivery possibility and it's cost."
        )
        total = (
            Decimal(cart.discounted_amount) - Decimal(delivery_discount)
        )
        reply_data['total'] = {
            "title": "Total amount, excl. delivery",
            "total_amount": total
            }

    else:
        reply_data['delivery_cost'] = delivery_cost
        total = (
            Decimal(cart.discounted_amount) - Decimal(delivery_discount) +
            Decimal(delivery_cost)
        )
        reply_data['total'] = {
            "title": "Total amount, incl. delivery",
            "total_amount": total
            }

    reply_data['amount'] = cart.amount
    reply_data['promocode'] = promocode
    reply_data['total_discount'] = (
        cart.discount + delivery_discount)


    return reply_data
