import os
import django

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_shop_with_bots.settings')  # Замените 'your_project' на имя вашего проекта
django.setup()

from django.contrib.auth import get_user_model
from audit.models import AuditLog


User = get_user_model()


def reset_first_order():
    users = User.objects.all().select_related('base_profile')
    for user in users:
        if user.base_profile.orders.filter(source='4').exists():
            base_profile = user.base_profile
            base_profile.first_web_order = True
            base_profile.save(update_fields=['first_web_order'])

        if user.base_profile.messenger_account:
            messenger = user.base_profile.messenger_account
            if hasattr(messenger, 'orders') and messenger.orders.exists():
                order = messenger.orders.first()
                order.transit_all_msngr_orders_to_base_profile(
                    user.base_profile)
            messenger.registered = True
            messenger.save(update_fields=['registered'])
    print("Successfully updated users")


def add_messenger_orders_to_base_account():
    """Проверить, есть ли заказы, привязанные к мессенджерам и привязать к base_account"""
    users = User.objects.all().select_related('base_profile')
    for user in users:
        if user.base_profile.messenger_account:
            messenger = user.base_profile.messenger_account
            if hasattr(messenger, 'orders') and messenger.orders.exists():
                order = messenger.orders.first()
                order.transit_all_msngr_orders_to_base_profile(
                    user.base_profile)
            messenger.registered = True
            messenger.save(update_fields=['registered'])
    print("Successfully updated users")



def audit_base_profile_add():
    auditlogs = AuditLog.objects.all()
    for log in auditlogs:
        if log.user:
            log.base_profile = log.user.base_profile

        if "ОТВЕТ: <!DOCTYPE html>" in log.details:
            log.status = '500'
        log.save(update_fields=['base_profile', 'status'])
    print("Successfully updated auditlogs")


if __name__ == '__main__':
    # reset_first_order()
    # audit_base_profile_add()
    print("Successfully updated users")
