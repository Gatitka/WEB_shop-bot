from django.contrib import admin

from .models import BaseProfile, WEBAccount, UserAddress
from shop.models import Order  # ShoppingCart
from django.contrib.auth.admin import UserAdmin


class WEBAccountAdminInline(admin.StackedInline):
    model = WEBAccount


class UserAddressesAdminInline(admin.TabularInline):
    model = UserAddress
    min_num = 0


@admin.register(BaseProfile)
class BaseProfileAdmin(admin.ModelAdmin):
    """Настройки отображения данных таблицы User."""
    list_display = ('id', 'is_active', 'first_name', 'last_name', 'phone', 'email', 'orders')
    # list_filter = ('first_name', 'last_name', 'phone')
    inlines = (UserAddressesAdminInline, WEBAccountAdminInline,)

    def orders(self, obj):
        return Order.objects.filter(user=obj.web_account.id).count()
    orders.short_description = 'заказы'

    def first_name(self, obj):
        return obj.web_account.first_name
    first_name.short_description = 'имя'

    def last_name(self, obj):
        return obj.web_account.last_name
    last_name.short_description = 'фамилия'

    def phone(self, obj):
        return obj.web_account.phone
    phone.short_description = 'телефон'

    def email(self, obj):
        return obj.web_account.email
    phone.short_description = 'email'
    # разработать переход из общего раздела клиент в webaccount, tmaccount


@admin.register(WEBAccount)
class WEBAccountAdmin(admin.ModelAdmin):
    """Настройки отображения данных таблицы User."""
