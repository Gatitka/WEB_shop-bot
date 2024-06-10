from .models import Order
from django.utils import timezone
from datetime import datetime
from openpyxl import Workbook
from django.http import HttpResponse


def get_filtered_orders_qs(start_date, end_date):
    if start_date is not None and end_date is not None:
        qs = Order.objects.filter(
                created__gte=start_date, created__lt=end_date
            ).select_related(
                'user',
                'delivery',
                'delivery_zone',
                'promocode',
                'restaurant'
            ).prefetch_related(
                'orderdishes__dish',
                'orderdishes__dish__translations'
            )
    else:
        qs = Order.objects.all().select_related(
                'user',
                'delivery',
                'delivery_zone',
                'promocode',
                'restaurant'
            ).prefetch_related(
                'orderdishes__dish',
                'orderdishes__dish__translations'
            )
    return qs


def export_full_orders_to_excel(modeladmin, request, queryset):
    # Получаем текущую дату для включения в имя файла
    current_date = datetime.now(timezone.utc).strftime('%d-%m-%Y')
    filename = f"orders_{current_date}_LARGE.xlsx"
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    start_date = request.GET.get('created__gte')
    end_date = request.GET.get('created__lt')

    queryset = get_filtered_orders_qs(start_date, end_date)

    # Создаем новый Excel-файл
    wb = Workbook()
    ws = wb.active

    ws.title = f"Orders_{current_date}"

    # Заголовки столбцов
    ws.append(['Order_Num', 'ID', 'Source',
               'Date',
               'Status', 'Is_first_order', 'Created_by',
               'Source',
               'User', 'Name',
               'Phone',
               'MSNGR',
               'Delivery',
               'Delivery_Time',
               'Address', 'Delivery_Zone',
               'Delivery_Cost',
               'Courier',
               'Payment',
               'Invoice',
               'Discount',
               'Discount amount',
               'Manual_discount', 'Amount',
               'Discounted_amount', 'Final_amount_with_shipping',
               ])

    # Добавляем данные из queryset
    for order in queryset:
        ws.append(
            [
                order.order_number, order.id, str(order.source),
                order.created.astimezone(None).strftime('%Y-%m-%d %H:%M:%S'),
                order.status, order.is_first_order, order.created_by,
                order.source,
                str(order.user), order.recipient_name,
                str(order.recipient_phone),
                order.msngr_account_id,
                order.delivery.type,
                (order.delivery_time.astimezone(None).strftime(
                    '%Y-%m-%d %H:%M:%S') if order.delivery_time else None),
                order.recipient_address, str(order.delivery_zone),
                order.delivery_cost,
                str(order.courier),
                order.payment_type,
                order.invoice,
                str(order.discount), order.discount_amount,
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
    # Получаем текущую дату для включения в имя файла
    current_date = datetime.now(timezone.utc).strftime('%d-%m-%Y')
    filename = f"orders_{current_date}.xlsx"
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    start_date = request.GET.get('created__gte')
    end_date = request.GET.get('created__lt')

    queryset = get_filtered_orders_qs(start_date, end_date)

    # Создаем новый Excel-файл
    wb = Workbook()
    ws = wb.active

    ws.title = f"Orders_{current_date}"

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

        ws.append(
            [
                order.order_number,
                address,
                order.discounted_amount,
                order.invoice,
                order.delivery_cost,
                str(order.courier)
            ]
        )

    # Сохраняем файл в HttpResponse
    wb.save(response)
    return response


export_orders_to_excel.short_description = (
    "Сохранить отчет по продажам в Excel.")
