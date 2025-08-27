import os
import django
import time
from decimal import Decimal

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_shop_with_bots.settings')
django.setup()

from shop.models import Order
from django.db.models import Max
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError


def edit_manual_discount():
    # Используем Decimal для точного сравнения с 10
    orders = Order.objects.filter(manual_discount=Decimal('10'),
                                  delivery__type='takeaway')
    updated_count = 0

    for order in orders:
        # Вычисляем абсолютное значение скидки
        discount_amount = order.amount - order.discounted_amount

        # Обновляем значение manual_discount
        order.manual_discount = discount_amount
        order.save(update_fields=['manual_discount'])
        updated_count += 1

    print(f"Successfully updated {updated_count} orders")

# def get_max_order_number_for_date(exec_date, restaurant):
#     """Получить максимальный номер заказа для указанной даты и ресторана"""
#     max_order = Order.objects.filter(
#         execution_date=exec_date,
#         restaurant=restaurant
#     ).aggregate(Max('order_number'))['order_number__max']

#     return 1 if max_order is None else max_order + 1


# def edit_execution_date():
#     count_total = Order.objects.count()
#     count_processed = 0
#     count_updated = 0
#     count_renumbered = 0

#     orders = Order.objects.all().order_by('created')

#     for order in orders:
#         count_processed += 1

#         # Определяем execution_date из даты создания заказа, а не из текущей даты
#         if order.delivery_time is None:
#             exec_date = order.created.date()
#         else:
#             exec_date = order.delivery_time.date()

#         # Пытаемся сохранить с текущим order_number, но минуя метод save()
#         try:
#             with transaction.atomic():
#                 update_fields = {'execution_date': exec_date}

#                 if order.source == '2':
#                     update_fields['source'] = '1'

#                 # Прямое обновление полей, минуя метод save()
#                 Order.objects.filter(id=order.id).update(**update_fields)
#                 count_updated += 1
#         except IntegrityError:
#             # Если возникла ошибка уникальности, назначаем новый order_number
#             new_order_number = get_max_order_number_for_date(exec_date, order.restaurant)

#             with transaction.atomic():
#                 update_fields = {
#                     'execution_date': exec_date,
#                     'order_number': new_order_number
#                 }

#                 if order.source == '2':
#                     update_fields['source'] = '1'

#                 # Прямое обновление полей, минуя метод save()
#                 Order.objects.filter(id=order.id).update(**update_fields)
#                 count_updated += 1
#                 count_renumbered += 1

#             print(f"Заказ ID {order.id} перенумерован на {new_order_number} для даты {exec_date}")

#         # Выводим прогресс
#         if count_processed % 100 == 0:
#             print(f"Обработано {count_processed}/{count_total}, обновлено: {count_updated}, перенумеровано: {count_renumbered}")

#     print(f"Успешно обновлено {count_updated} заказов из {count_total}")
#     print(f"Перенумеровано заказов: {count_renumbered}")


# def edit_payment_type():
#     orders = Order.objects.all()
#     for order in orders:
#         if order.status == 'DLD':
#             order.status = 'OND'
#             order.save(update_fields=['status'])

#         # if order.payment_type is None:
#         #     order.payment_type = 'cash'
#         #     order.save(update_fields=['payment_type'])

#     print("Successfully updated orders")


if __name__ == '__main__':
    edit_manual_discount()
    # reset_first_order()
    # audit_base_profile_add()
    # edit_execution_date()
    print("Successfully updated users")
