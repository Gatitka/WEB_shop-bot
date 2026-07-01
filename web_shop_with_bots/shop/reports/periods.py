from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone


def get_range_period(request):
    """
    Поддерживает:
    - execution_date__gte / execution_date__lt
    - execution_date__range__gte / execution_date__range__lte
    - quick filter order_period = yesterday/today/tomorrow/future
    """
    start_date = end_date = None
    start_pref = end_pref = None

    start_date_data = request.GET.get('execution_date__gte')
    if start_date_data is not None:
        start_date = datetime.strptime(start_date_data, '%Y-%m-%d %H:%M:%S%z')
        start_pref = 'gte'
    else:
        start_date_data = request.GET.get('execution_date__range__gte')
        if start_date_data is not None:
            start_date = datetime.strptime(start_date_data, '%d.%m.%Y')
            start_pref = 'gte'

    end_date_data = request.GET.get('execution_date__lt')
    if end_date_data is not None:
        end_date = datetime.strptime(end_date_data, '%Y-%m-%d %H:%M:%S%z')
        end_pref = 'lt'
    else:
        end_date_data = request.GET.get('execution_date__range__lte')
        if end_date_data is not None:
            end_date = (
                datetime.strptime(end_date_data, '%d.%m.%Y')
                + timedelta(days=1)
                - timedelta(seconds=1)
            )
            end_pref = 'lte'

    if start_date is None and end_date is None:
        order_period = request.GET.get('order_period')
        today = timezone.localdate()

        if order_period == 'yesterday':
            d = today - timedelta(days=1)
            start_date = d
            end_date = d
            start_pref = 'gte'
            end_pref = 'lte'
        elif order_period == 'today':
            start_date = today
            end_date = today
            start_pref = 'gte'
            end_pref = 'lte'
        elif order_period == 'tomorrow':
            d = today + timedelta(days=1)
            start_date = d
            end_date = d
            start_pref = 'gte'
            end_pref = 'lte'
        elif order_period == 'future':
            start_date = today + timedelta(days=1)
            end_date = None
            start_pref = 'gt_or_gte'
            end_pref = None

    return start_date, start_pref, end_date, end_pref


def get_file_data(start_date, end_date, current_date, report_type):
    if start_date is not None and end_date is not None:
        start_date_str = datetime.strftime(start_date, '%d.%m.%Y')
        end_date_str = datetime.strftime(end_date, '%d.%m.%Y')
        filename = (
            f"{report_type}_orders_{start_date_str}-{end_date_str}_crtd_at_{current_date}.xlsx"
        )
        ws_title = f"Orders_{start_date_str}-{end_date_str}"
        first_row = f"Период заказов: {start_date_str} - {end_date_str}"
    elif start_date is not None and end_date is None:
        start_date_str = datetime.strftime(start_date, '%d.%m.%Y')
        filename = f"{report_type}_orders_from_{start_date_str}_crtd_at_{current_date}.xlsx"
        ws_title = f"Orders_from_{start_date_str}"
        first_row = f"Период заказов: с {start_date_str}"
    else:
        filename = f"orders_ALL_crtd_at_{current_date}.xlsx"
        ws_title = 'Orders_ALL'
        first_row = 'Период заказов: все заказы'

    return filename, ws_title, first_row


def build_execution_date_filter(prefix: str, start_date, end_date, end_pref):
    q = Q()

    if start_date is not None and end_date is not None:
        if end_pref == 'lt':
            q &= Q(**{f'{prefix}__gte': start_date}) & Q(**{f'{prefix}__lt': end_date})
        elif end_pref == 'lte':
            q &= Q(**{f'{prefix}__gte': start_date}) & Q(**{f'{prefix}__lte': end_date})
    elif start_date is not None and end_date is None:
        q &= Q(**{f'{prefix}__gte': start_date})

    return q
