from django.db.models import Prefetch

from shop.models import Order, OrderDish

from .periods import build_execution_date_filter


def get_filtered_orders_qs(start_date, start_pref, end_date, end_pref, admin):
    """Если не переданы временные рамки, берём все заказы."""
    filter_q = build_execution_date_filter(
        'execution_date',
        start_date=start_date,
        end_date=end_date,
        end_pref=end_pref,
    )

    if getattr(admin, 'restaurant', None):
        from django.db.models import Q
        filter_q &= Q(restaurant=admin.restaurant)

    return Order.objects.filter(filter_q).select_related(
        'user',
        'delivery',
        'delivery_zone',
        'restaurant',
        'courier',
        'discount',
        'msngr_account',
        'campaign'
    ).order_by('execution_date', 'order_number', 'id')


def get_filtered_orderdishes_qs(start_date, start_pref, end_date, end_pref, admin):
    filter_q = build_execution_date_filter(
        'order__execution_date',
        start_date=start_date,
        end_date=end_date,
        end_pref=end_pref,
    )

    if getattr(admin, 'restaurant', None):
        from django.db.models import Q
        filter_q &= Q(order__restaurant=admin.restaurant)

    return OrderDish.objects.filter(filter_q).select_related(
        'order',
        'dish',
        'order__user',
        'order__delivery',
        'order__delivery_zone',
        'order__restaurant',
        'order__courier',
        'order__discount',
        'order__msngr_account',
    # ).prefetch_related(
    #     Prefetch('dish__translations'),
    ).order_by('order__execution_date', 'order__order_number', 'id')
