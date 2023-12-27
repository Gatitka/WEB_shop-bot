from django.contrib import admin

from .models import BaseProfile, WEBAccount, UserAddress
from shop.models import Order  # ShoppingCart
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count


class WEBAccountAdminInline(admin.StackedInline):
    model = WEBAccount


class UserAddressesAdminInline(admin.TabularInline):
    model = UserAddress
    min_num = 0


@admin.register(BaseProfile)
class BaseProfileAdmin(admin.ModelAdmin):
    """Настройки отображения данных таблицы User."""
    list_display = ('id', 'is_active', 'first_name', 'last_name', 'phone', 'email', 'orders')
    list_search = ('first_name', 'last_name', 'phone', 'email')
    list_filter = ('is_active',)
    list_select_related = ['web_account', 'my_addresses']
    inlines = (UserAddressesAdminInline, WEBAccountAdminInline,)

    def get_queryset(self, request):
        qs = BaseProfile.objects.select_related(
            'web_account'
            ).select_related(
                'my_addresses'
                ).annotate(orders_qty=Count('orders')).all()
        return qs

    def orders(self, obj):
        ord_num = Order.objects.filter(user=obj.pk).count()
        return ord_num
    orders.short_description = 'заказы'

    def first_name(self, obj):
        try:
            return obj.web_account.first_name
        except AttributeError:
            return 'no first_name'
    first_name.short_description = 'имя'

    def last_name(self, obj):
        try:
            return obj.web_account.last_name
        except AttributeError:
            return 'no last_name'
    last_name.short_description = 'фамилия'

    def phone(self, obj):
        try:
            return obj.web_account.phone
        except AttributeError:
            return 'no phone'
    phone.short_description = 'телефон'

    def email(self, obj):
        try:
            return obj.web_account.email
        except AttributeError:
            return 'no email'
    phone.short_description = 'email'
    # разработать переход из общего раздела клиент в webaccount, tmaccount


@admin.register(WEBAccount)
class WEBAccountAdmin(admin.ModelAdmin):
    """Настройки отображения данных таблицы User."""
    list_display = ('id', 'email')
    list_search = ('email', 'is_active', 'first_name', 'last_name', 'phone', )
    list_filter = ('is_active',)
