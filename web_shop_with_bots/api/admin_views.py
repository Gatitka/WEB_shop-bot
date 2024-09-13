from django.contrib.admin.views.decorators import staff_member_required
from shop.models import Order
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.db.models.functions import TruncDay
import datetime


@staff_member_required
def sales_data(request):
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    date_range = [(last_30_days + timedelta(days=i)) for i in range(31)]

    def fill_missing_dates(queryset, date_range):
        data_dict = {entry['day'].date(): entry['total'] for entry in queryset}
        filled_data = [{'day': day, 'total': data_dict.get(day, 0)} for day in date_range]
        return filled_data

    def fill_missing_order_dates(queryset, date_range):
        data_dict = {entry['day'].date(): entry['total_orders'] for entry in queryset}
        filled_data = [{'day': day, 'total_orders': data_dict.get(day, 0)} for day in date_range]
        return filled_data

    base_filter = Q(created__gte=timezone.make_aware(
                            datetime.datetime.combine(
                                last_30_days,
                                datetime.datetime.min.time())))
    web_filter = Q(source='4')
    bot_filter = Q(source='3')

    base_filter_q = base_filter
    base_web_filter_q = base_filter & web_filter
    base_bot_filter_q = base_filter & bot_filter

    user = request.user

    if user.restaurant:
        restaurant_filter = Q(restaurant=user.restaurant)
        base_filter_q &= restaurant_filter
        base_web_filter_q &= restaurant_filter
        base_bot_filter_q &= restaurant_filter

    # Запросы для подсчета общих продаж по дням
    total_sales_qs = Order.objects.filter(
            base_filter_q
        ).annotate(day=TruncDay('created')).values('day').annotate(
            total=Sum('final_amount_with_shipping')
        ).order_by('day')
    total_sales = fill_missing_dates(total_sales_qs, date_range)

    # Запросы для подсчета продаж с сайта (source='4') по дням
    site_sales_qs = Order.objects.filter(
            base_web_filter_q
        ).annotate(day=TruncDay('created')).values('day').annotate(
            total=Sum('final_amount_with_shipping')
        ).order_by('day')
    site_sales = fill_missing_dates(site_sales_qs, date_range)

    # Запросы для подсчета продаж с бота (source='3') по дням
    bot_sales_qs = Order.objects.filter(
            base_bot_filter_q
        ).annotate(day=TruncDay('created')).values('day').annotate(
            total=Sum('final_amount_with_shipping')
        ).order_by('day')
    bot_sales = fill_missing_dates(bot_sales_qs, date_range)

    # Запросы для подсчета общего количества заказов по дням
    total_orders_qs = Order.objects.filter(
            base_filter_q
        ).annotate(day=TruncDay('created')).values('day').annotate(
            total_orders=Count('id')
        ).order_by('day')
    total_orders = fill_missing_order_dates(total_orders_qs, date_range)

    # Запросы для подсчета количества заказов с сайта (source='4') по дням
    site_orders_qs = Order.objects.filter(
            base_web_filter_q
        ).annotate(day=TruncDay('created')).values('day').annotate(
            total_orders=Count('id')
        ).order_by('day')
    site_orders = fill_missing_order_dates(site_orders_qs, date_range)

    # Запросы для подсчета количества заказов с бота (source='3') по дням
    bot_orders_qs = Order.objects.filter(
            base_bot_filter_q
        ).annotate(day=TruncDay('created')).values('day').annotate(
            total_orders=Count('id')
        ).order_by('day')
    bot_orders = fill_missing_order_dates(bot_orders_qs, date_range)

    data = {
        'total_sales': total_sales,
        'site_sales': site_sales,
        'bot_sales': bot_sales,
        'total_orders': total_orders,
        'site_orders': site_orders,
        'bot_orders': bot_orders,
    }

    for key, value in data.items():
        for item in value:
            item['day'] = datetime.datetime.combine(
                item['day'],
                datetime.datetime.min.time())

    return JsonResponse(data)
