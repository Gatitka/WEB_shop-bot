from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class ShopAdminConfig(AdminConfig):
    default_site = 'shop.admin.ShopAdminArea'


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'
    verbose_name = '1. Продажи'

    def ready(self):
        import shop.signals
