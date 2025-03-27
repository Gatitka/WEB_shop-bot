import os
import django
import time

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_shop_with_bots.settings')
django.setup()

from shop.models import Order


def edit_payment_type():
    orders = Order.objects.all()
    for order in orders:
        if order.status == 'DLD':
            order.status = 'OND'
            order.save(update_fields=['status'])

        # if order.payment_type is None:
        #     order.payment_type = 'cash'
        #     order.save(update_fields=['payment_type'])

    print("Successfully updated orders")


if __name__ == '__main__':
    # reset_first_order()
    # audit_base_profile_add()
    edit_payment_type()
    print("Successfully updated users")
