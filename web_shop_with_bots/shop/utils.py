from django.db.models import Max
from django.utils import timezone
from datetime import datetime
from openpyxl import Workbook
from django.http import HttpResponse


def get_next_item_id_today(model, field):
    today_start = timezone.localtime(
        timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    # Начало текущего дня

    today_end = (
        today_start + timezone.timedelta(days=1)
        - timezone.timedelta(microseconds=1)  # Конец текущего дня
    )

    max_id = model.objects.filter(
        created__range=(today_start, today_end)
    ).aggregate(Max(field))[f'{field}__max']

    # Устанавливаем номер заказа на единицу больше MAX текущей даты
    if max_id is None:
        return 1
    else:
        return max_id + 1


def get_first_item_true(obj):
    # проверка на первый заказ
    model_class = obj.__class__
    if obj.user is not None:
        if not model_class.objects.filter(user=obj.user).exists():
            return True
    else:
        if not model_class.objects.filter(
            recipient_phone=obj.recipient_phone
        ).exists():
            return True
    return False


def split_and_get_comment(input_string):
    # Разделение строки по подстроке "comment from user:"
    parts = input_string.split(",  comment from user:")

    # Если подстрока найдена
    if len(parts) > 1:
        # Получение всех символов до подстроки
        address_comment = parts[0].strip()
        comment = parts[1].strip()
    else:
        address_comment, comment = None, None

    return address_comment, comment


'flat: 5, floor: 5, interfon: 5,  comment from user:5\\57'


def export_orders_to_excel(modeladmin, request, queryset):
    # Получаем текущую дату для включения в имя файла
    current_date = datetime.now(timezone.utc).strftime('%d-%m-%Y')
    filename = f"orders_{current_date}.xlsx"
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Создаем новый Excel-файл
    wb = Workbook()
    ws = wb.active

    ws.title = f"Orders_{current_date}"

    # Заголовки столбцов
    ws.append(['Order_Num', 'ID',
               'Date',
               'Status', 'Is_first_order', 'Created_by',
               'User', 'Name',
               'Phone',
               'Delivery',
               'Delivery_Time',
               'Address', 'Delivery_Zone',
               'Delivery_Cost',
               'Dish', 'Q-ty',
               'Payment', 'Auth_fst_ord_disc_amount',
               'Takeaway_disc_amount', 'Cash_discount_amount',
               'Manual_discount',
               'Discounted_amount', 'Final_amount_with_shipping',
               ])

    # Добавляем данные из queryset
    for order in queryset:
        ws.append(
            [
                order.order_number, order.id,
                order.created.astimezone(None).strftime('%Y-%m-%d %H:%M:%S'),
                order.status, order.is_first_order, order.created_by,
                str(order.user), order.recipient_name,
                str(order.recipient_phone),
                order.delivery.type,
                (order.delivery_time.astimezone(None).strftime(
                    '%Y-%m-%d %H:%M:%S') if order.delivery_time else None),
                order.recipient_address, str(order.delivery_zone),
                order.delivery_cost,
                order.payment_type,
                order.auth_fst_ord_disc_amount, order.takeaway_disc_amount,
                order.cash_discount_amount, order.manual_discount,
                order.discounted_amount, order.final_amount_with_shipping,
            ]
        )

    # Сохраняем файл в HttpResponse
    wb.save(response)
    return response


export_orders_to_excel.short_description = (
    "Сохранить отчет по продажам в Excel.")
