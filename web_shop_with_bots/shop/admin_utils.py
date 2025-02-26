from .models import Order
from delivery_contacts.models import Restaurant
from django.utils import timezone
from datetime import datetime, timedelta
from openpyxl import Workbook
from django.http import HttpResponse
from django.db.models import Q
from django.utils.timezone import make_aware
from django.db.models import Sum, Count
from django.conf import settings
from decimal import Decimal


def get_range_period(request):
    start_date_data = request.GET.get('created__gte')
    if start_date_data is not None:
        start_date = datetime.strptime(start_date_data,
                                       '%Y-%m-%d %H:%M:%S%z')
    else:
        start_date_data = request.GET.get('created__range__gte')
        if start_date_data is not None:
            start_date = datetime.strptime(start_date_data,
                                           '%d.%m.%Y')
    start_pref = 'gte'

    end_date_data = request.GET.get('created__lt')
    if end_date_data is not None:
        end_date = datetime.strptime(end_date_data,
                                     '%Y-%m-%d %H:%M:%S%z')
        end_pref = 'lt'
    else:
        end_date_data = request.GET.get('created__range__lte')
        if end_date_data is not None:
            end_date = (datetime.strptime(end_date_data,
                                          '%d.%m.%Y')
                        + timedelta(days=1) - timedelta(seconds=1))
            end_pref = 'lte'

    if (start_date_data is None
            and end_date_data is None):
        start_date, start_pref, end_date, end_pref = None, None, None, None

    return start_date, start_pref, end_date, end_pref


def get_file_data(start_date, end_date, current_date, type):
    if (start_date is not None
            and end_date is not None):
        start_date_str = datetime.strftime(start_date, '%d.%m.%Y')
        end_date_str = datetime.strftime(end_date, '%d.%m.%Y')
        filename = (f"{type}_orders_{start_date_str}-"
                    f"{end_date_str}_crtd_at_"
                    f"{current_date}.xlsx")
        ws_title = f"Orders_{start_date_str}-{end_date_str}"
        first_row = f"Период заказов: {start_date_str} - {end_date_str}"

    else:
        filename = (f"orders_ALL_crtd_at_"
                    f"{current_date}.xlsx")
        ws_title = "Orders_ALL"
        first_row = "Период заказов: все заказы"
    return filename, ws_title, first_row


def get_filtered_orders_qs(start_date, start_pref, end_date, end_pref, admin):
    """Если не переданы рамки временные, то берем все заказы"""
    filter_q = Q()
    if start_date is not None and end_date is not None:
        if end_pref == 'lt':
            filter_q &= Q(created__gte=start_date) & Q(created__lt=end_date)
        elif end_pref == 'lte':
            filter_q &= Q(created__gte=start_date) & Q(created__lte=end_date)

    if admin.restaurant:
        filter_q &= Q(restaurant=admin.restaurant)

    #qs = Order.objects.filter(created__gte=start_date, created__lte=end_date).select_related(
    qs = Order.objects.filter(filter_q).select_related(
                'user',
                'delivery',
                'delivery_zone',
                'promocode',
                'restaurant',
                'courier'
            ).prefetch_related(
                'orderdishes__dish',
                'orderdishes__dish__translations'
            )

    return qs


def export_full_orders_to_excel(modeladmin, request, queryset):
    start_date, start_pref, end_date, end_pref = get_range_period(request)
    current_date = datetime.now(timezone.utc).strftime('%d-%m-%Y')

    filename, ws_title, first_row = get_file_data(start_date, end_date,
                                                  current_date, 'LARGE')

    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    admin = request.user
    queryset = get_filtered_orders_qs(start_date, start_pref,
                                      end_date, end_pref, admin)

    # Создаем новый Excel-файл
    wb = Workbook()
    ws = wb.active

    ws.title = ws_title

    # Вставляем первую строку с периодом заказов
    ws.insert_rows(1)
    ws.cell(row=1, column=1).value = first_row

    # Заголовки столбцов
    ws.append(['Order_Num', 'ID', 'Source',
               'Date', 'Time',
               'Status', 'Is_first_order', 'Created_by',
               'Source',
               'User', 'Name',
               'Phone',
               'MSNGR_ID', 'MSNGR_USERNAME',
               'Delivery',
               'Delivery_Time',
               'Address', 'Delivery_Zone',
               'Courier',
               'Payment',
               'Invoice',
               'Discount', 'Delivery_Cost',
               'Discount amount',
               'Manual_discount', 'Amount',
               'Discounted_amount', 'Final_amount_with_shipping',
               ])

    # Добавляем данные из queryset
    for order in queryset:

        if order.is_first_order:
            is_first_order = 'yes'
        else:
            is_first_order = ''

        if order.invoice:
            invoice = 1
        else:
            invoice = ''

        ws.append(
            [
                order.order_number, order.id, str(order.source),
                order.created.astimezone(None).strftime('%Y-%m-%d'),
                order.created.astimezone(None).strftime('%H:%M:%S'),
                order.status, is_first_order, order.created_by,
                order.source,
                str(order.user), order.recipient_name,
                str(order.recipient_phone),
                order.msngr_account.msngr_id if order.msngr_account is not None else '',
                order.msngr_account.msngr_username if order.msngr_account is not None else '',
                order.delivery.type,
                (order.delivery_time.astimezone(None).strftime(
                    '%Y-%m-%d %H:%M:%S') if order.delivery_time else None),
                order.recipient_address, str(order.delivery_zone),
                str(order.courier),
                order.payment_type,
                invoice,
                str(order.discount), order.delivery_cost, order.discount_amount,
                order.manual_discount,
                order.amount,
                order.discounted_amount, order.final_amount_with_shipping,
            ]
        )

    # Сохраняем файл в HttpResponse
    wb.save(response)
    return response


export_full_orders_to_excel.short_description = (
    "Сохранить ПОЛНЫЙ отчет по продажам в Excel.")


def export_orders_to_excel(modeladmin, request, queryset):
    start_date, start_pref, end_date, end_pref = get_range_period(request)
    current_date = datetime.now(timezone.utc).strftime('%d-%m-%Y')

    filename, ws_title, first_row = get_file_data(start_date, end_date,
                                                  current_date, 'SHORT')

    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    admin = request.user
    queryset = get_filtered_orders_qs(start_date, start_pref,
                                      end_date, end_pref, admin)

    # Создаем новый Excel-файл
    wb = Workbook()
    ws = wb.active

    ws.title = ws_title

    # Вставляем первую строку с периодом заказов
    ws.insert_rows(1)
    ws.cell(row=1, column=1).value = first_row

    # Заголовки столбцов
    ws.append(['Заказ',
               'Адрес',
               'Сумма',
               'Чек',
               'Стоимость доставки',
               'Курьер',
               ])

    # Добавляем данные из queryset
    for order in queryset:
        if order.delivery.type == 'delivery':
            address = order.recipient_address
        else:
            if order.source in ['1', '3', '4']:
                address = 'самовывоз'
            elif order.source == ['P1-1']:
                address = "GLOVO"
            elif order.source == ['P1-2']:
                address = "WOLT"
            elif order.source == ['P2-1']:
                address = "SMOKE"

        if order.invoice:
            invoice = 1
        else:
            invoice = ''

        ws.append(
            [
                order.order_number,
                address,
                order.discounted_amount,
                invoice,
                order.delivery_cost,
                str(order.courier)
            ]
        )

    # Сохраняем файл в HttpResponse
    wb.save(response)
    return response


export_orders_to_excel.short_description = (
    "Сохранить отчет по продажам в Excel.")


def get_changelist_extra_context(request, extra_context, source=None):
    extra_context = extra_context or {}
    view = request.GET.get('view', None)
    e = request.GET.get('e', None)

    today = timezone.now().date()
    filters = {
               'created__date': today
                }
    if source:
        filters['source'] = source

    if request.user.is_superuser or view == 'all_orders' or e == '1':
        # собираем данные по заказам:
        # если есть сорс, то определнный тип заказа во всех ресторанах
        # если нет сорса, то все типы заказов во всех ресторанах
        title = "Заказы всех ресторанов"

    else:
        # собираем данные по ресторану
        restaurant = request.user.restaurant
        filters['restaurant'] = restaurant
        title = f"Заказы ресторана: {restaurant.city}/{restaurant.address}"

    today_orders = Order.objects.filter(
                **filters
            ).select_related(
                'delivery',
                'delivery_zone',
                'courier')

    #Разбираем заказы по типам для дальнейшего анализа
    delivery_orders = []
    takeaway_orders = []
    for order in today_orders:
        if order.delivery.type == 'delivery':
            delivery_orders.append(order)
        else:
            takeaway_orders.append(order)
    partners_orders = today_orders.filter(source__in=settings.PARTNERS_LIST)

    # Calculate the total discounted amount and total receipts
    total_amount = sum(order.final_amount_with_shipping for order in today_orders)
    total_qty = today_orders.count()
    total_receipts = sum(order.invoice for order in today_orders)

    # Calculate total takeaways
    total_nocash = (sum(order.final_amount_with_shipping for order in takeaway_orders if order.payment_type == 'cash' and order.invoice is False)
                    + sum(order.final_amount_with_shipping for order in partners_orders if order.source == 'P2-2'))    # не та дверь платит налом без чека
    total_gotovina = sum(order.final_amount_with_shipping for order in takeaway_orders if order.payment_type == 'cash' and order.invoice is True)
    total_card = sum(order.final_amount_with_shipping for order in takeaway_orders if order.payment_type in ['card', 'card_on_delivery'])

    total_smoke = sum(order.final_amount_with_shipping for order in partners_orders if order.source == 'P2-1')  #('P2-1', 'Smoke'),
    total_curiers = sum(order.final_amount_with_shipping for order in delivery_orders if order.payment_type == 'cash')
    total_terminal = total_amount - total_nocash - total_smoke - total_curiers

    # if request.user.is_superuser or view == 'all_orders' or e == '1':
    #     city_totals = (
    #         today_orders
    #         .values('city')
    #         .annotate(
    #             ttl_city_am=Sum('final_amount_with_shipping'),
    #             ttl_city_qty=Count('id'),
    #             ttl_city_rct=Count('invoice')
    #         )
    #     )
    #     # Преобразуем QuerySet в список словарей
    #     extra_context['city_totals'] = [
    #         {
    #             "city": city['city'],
    #             "ttl_city_am":
    #                 f"{city['ttl_city_am']:.2f} ({city['ttl_city_qty']} зак.)",
    #             "ttl_city_rct": city['ttl_city_rct'],
    #         }
    #         for city in city_totals
    #     ]

    # Prepare partners data
    SOURCE_DICT = dict(settings.SOURCE_TYPES)
    partners = {}
    for order in partners_orders:
        partner_name = SOURCE_DICT[order.source]
        if partner_name in partners:
            partners[partner_name] += order.final_amount_with_shipping
        else:
            partners[partner_name] = order.final_amount_with_shipping

    # Prepare couriers data
    couriers = {}
    for order in delivery_orders:
        courier_name = order.courier if order.courier else 'Unknown'
        unclarified = False

        if order.delivery_zone.delivery_cost != float(0):
            delivery_cost = order.delivery_zone.delivery_cost
        elif order.delivery_zone.name == 'уточнить':
            delivery_cost = order.delivery_cost
            unclarified = True
        elif order.delivery_zone.name == 'по запросу':
            delivery_cost = order.delivery_cost

        if courier_name in couriers:
            couriers[courier_name][0] += delivery_cost
        else:
            couriers[courier_name] = [Decimal('0'), False,
                                      Decimal('0'), Decimal('0'),
                                      Decimal('0')]
            if order.courier:
                couriers[courier_name][4] = order.courier.min_payout

            couriers[courier_name][0] = delivery_cost
        couriers[courier_name][1] = unclarified

        if order.payment_type == 'cash':
            couriers[courier_name][2] += order.final_amount_with_shipping
        if order.payment_type in ['card', 'card_on_delivery']:
            couriers[courier_name][3] += order.final_amount_with_shipping

    for courier in couriers:
        couriers[courier][0] += couriers[courier][4]

    extra_context['title'] = title
    total_amount_str = f"{total_amount:.2f} ({total_qty} зак.)"
    extra_context['total_amount'] = total_amount_str
    extra_context['total_receipts'] = total_receipts
    extra_context['total_nocash'] = float(total_nocash)
    extra_context['total_gotovina'] = float(total_gotovina)
    extra_context['total_card'] = total_card
    extra_context['total_curiers'] = total_curiers
    extra_context['total_terminal'] = total_terminal
    extra_context['partners'] = partners
    extra_context['couriers'] = couriers
    return extra_context


def my_get_object(model, object_id, source=None):
    # Определяем поля для использования в запросе
    select_related_fields = [
        'restaurant',
    ]
    prefetch_related_fields = [
        'orderdishes__dish__translations',
        # 'orderdishes__dish__article',
    ]
    if source is None:
        select_related_fields += [
            'delivery',
            'delivery_zone',
            'msngr_account',
            'courier',
            'promocode',
            'courier',
        ]
        prefetch_related_fields += [
            'user',
            'user__messenger_account'
        ]

    # Создаем запрос для конкретного объекта с нужными связями
    try:
        order = model.objects.select_related(
                    *select_related_fields
                ).prefetch_related(
                    *prefetch_related_fields
                ).get(pk=int(object_id))
        return order
    except model.DoesNotExist:
        return None


def my_get_queryset(request, qs):
    if request.user.is_superuser:
        return qs
    view = request.GET.get('view', None)
    e = request.GET.get('e', None)
    if view == 'all_orders' or e == '1':
        return qs
    restaurant = request.user.restaurant
    if restaurant:
        qs = qs.filter(restaurant=restaurant)
        return qs
