from django.db.models import Prefetch
from decimal import Decimal
from .models import CartDish, ShoppingCart, Discount
from users.models import BaseProfile
from .validators import cart_valiation
from decimal import Decimal
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from promos.services import get_promocode_discount_amount
from django.conf import settings


def get_base_profile_w_cart(current_user):
    return BaseProfile.objects.filter(
        web_account=current_user
    ).first()

    # if base_profile and hasattr(base_profile, 'shopping_cart'):
    #     return BaseProfile.objects.filter(
    #         web_account=current_user,
    #     ).select_related(
    #         'shopping_cart',
    #         'shopping_cart__promocode'
    #     ).prefetch_related(
    #         'shopping_cart__cartdishes'
    #     ).first()
    # else:


def get_cart_base_profile(base_profile, validation=True, half_validation=False):

    if hasattr(base_profile, 'shopping_cart'):
        # Если есть связанный объект ShoppingCart, используйте его
        cart, created = ShoppingCart.objects.get_or_create(
            user=base_profile,
            complited=False
        )

        if created is False:
            if validation:
                cart_valiation(cart, half_validation)

    return cart


def get_cart(current_user, validation=True, half_validation=False):
    """ Функция достает корзину клиента, получив current_user = request.user"""
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


def get_cart_detailed(current_user):
    cart = ShoppingCart.objects.filter(
                user=current_user.base_profile,
                complited=False
            ).select_related(
                'promocode'
            ).prefetch_related(

                Prefetch(
                    'cartdishes',
                    queryset=CartDish.objects.all(
                    ).select_related(
                        'dish'
                    ).prefetch_related(
                        'dish__translations'
                    )
                )
            ).first()
        # попробовать свернуть получение вместе с base_profile
        # cart = get_cart(current_user, validation=False)
        # не исп, т.к. значительно в разы утяжеляет запросы и время

    if cart is None:
        cart = ShoppingCart.objects.create(
            user=current_user.base_profile
        )

    return cart


def find_uncomplited_cart_to_complete(base_profile):

    if hasattr(base_profile, 'shopping_cart'):
        # Если есть связанный объект ShoppingCart, используйте его
        cart = ShoppingCart.objects.filter(
                    user=base_profile,
                    complited=False
               ).first()

        if cart:
            cart.complited = True
            cart.save()


def base_profile_first_order(current_user):
    has_no_orders = BaseProfile.objects.filter(
        web_account=current_user,
        orders_qty=0
    ).exists()

    return has_no_orders


def get_cash_discount():
    return Discount.objects.filter(type='2', is_active=True).first()
