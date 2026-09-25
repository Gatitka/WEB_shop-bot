from django.db.models import Sum, Count, Q
from django.utils import timezone

from shop.models import Order


def get_restaurant_partner_stats(period: str, month: int | None = None,
                                 year: int | None = None) -> dict:
    """
    period: 'today' | 'month'
    month/year: только для period='month'; если не переданы — берётся
    текущий месяц/год.

    Учитываются только заказы:
    - city='Beograd', delivery__type='restaurant'
    - не отменённые (status != 'CND')
    - время исполнения которых уже наступило:
      delivery_time is None (заказ "как можно скорее") ИЛИ delivery_time <= сейчас
      (заказы, оформленные на будущее время/дату, не считаются)
    """
    now = timezone.localtime()
    today = now.date()

    qs = Order.objects.filter(
        city='Beograd',
        delivery__type='restaurant',
    ).exclude(status='CND').filter(
        Q(delivery_time__isnull=True) | Q(delivery_time__lte=now)
    )

    if period == 'today':
        qs = qs.filter(execution_date=today)
    elif period == 'month':
        target_month = month or today.month
        target_year = year or today.year
        qs = qs.filter(execution_date__year=target_year,
                       execution_date__month=target_month)

    agg = qs.aggregate(
        total_sum=Sum('final_amount_with_shipping'),
        orders_count=Count('id'),
    )

    total_sum = agg['total_sum'] or 0
    orders_count = agg['orders_count'] or 0
    avg_check = (total_sum / orders_count) if orders_count else 0

    return {
        'total_sum': total_sum,
        'orders_count': orders_count,
        'avg_check': avg_check,
    }
