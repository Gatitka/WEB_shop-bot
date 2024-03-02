from users.models import BaseProfile
from shop.models import CartDish, Order, OrderDish, ShoppingCart
from rest_framework import status
from rest_framework.response import Response


def get_cart(current_user):
    base_profile = get_base_profile_w_cart(current_user)
    if base_profile and base_profile.shopping_cart:
        return base_profile.shopping_cart
    return None


def get_base_profile_and_shopping_cart(current_user):
    base_profile = get_base_profile_w_cart(current_user)
    cart = None
    if base_profile and base_profile.shopping_cart:
        cart = base_profile.shopping_cart
    return base_profile, cart


def get_base_profile_w_cart(current_user):
    return BaseProfile.objects.filter(
        web_account=current_user
    ).select_related(
        'shopping_cart'
    ).prefetch_related(
        'shopping_cart__cartdishes'
    ).first()


def get_cart_base_profile(base_profile):
    cart = base_profile.shopping_cart

    if cart is None:
        return Response(
            {
                "error":
                    ("Ошибка при проверке корзины, "
                     "попробуйте собрать корзину еще раз.")
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if not cart.cartdishes.exists():
        return Response(
            {
                "error":
                    ("Корзина пуста. Пожалуйста, добавьте блюда в "
                        "корзину перед оформлением заказа.")
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    return cart
