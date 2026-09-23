from django.db.models import Sum, Count
from django.utils import timezone

from shop.models import Order


def get_restaurant_partner_stats(period: str) -> dict:
    """
    period: 'today' | 'month'
    Статистика по заказам city='Beograd', delivery__type='restaurant',
    исключая отменённые (CND). Считаем по execution_date — дате факта
    исполнения заказа, а не по дате создания.
    """
    today = timezone.localdate()
    qs = Order.objects.filter(
        city='Beograd',
        delivery__type='restaurant',
    ).exclude(status='CND')

    if period == 'today':
        qs = qs.filter(execution_date=today)
    elif period == 'month':
        qs = qs.filter(execution_date__year=today.year,
                       execution_date__month=today.month)

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
