from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count
from django import forms
from shop.models import Order  # ShoppingCart

from .models import BaseProfile, UserAddress, WEBAccount
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.core.exceptions import ValidationError


class UserAddressesAdminInline(admin.TabularInline):
    model = UserAddress
    min_num = 0
    extra = 0   # чтобы не добавлялись путые поля


@admin.register(BaseProfile)
class BaseProfileAdmin(admin.ModelAdmin):
    """Настройки отображения данных таблицы User."""
    list_display = ('id', 'is_active', 'first_name', 'last_name', 'phone', 'email', 'orders')
    search_fields = ('first_name', 'last_name', 'phone', 'email')
    list_filter = ('is_active',)
    list_select_related = ['web_account', 'my_addresses']
    readonly_fields = ('date_joined', 'orders',
                       'first_name', 'last_name', 'phone', 'email')
    inlines = (UserAddressesAdminInline,)
    fieldsets = (
        ('Основное', {
            'fields': (
                ('first_name', 'last_name'),
                ('date_of_birth', 'is_active'),
                ('date_joined'),
            )
        }),
        ('Контакты', {
            'fields': (
                ('phone'),
                ('email'),
                ('city'),
                ('base_language'),
            )
        }),
        ('Пользователь сайта, мессенджера', {
            'fields': (
                ('web_account'),
                ('messenger_account'),
            )
        }),
        ('Комментарии', {
            'fields': (
                ('notes', 'orders')
            )
        }),
    )

    def get_queryset(self, request):
        qs = BaseProfile.objects.prefetch_related(
            'web_account'
            ).prefetch_related(
                'my_addresses'
                ).annotate(orders_qty=Count('orders')).all()
        return qs

    def orders(self, obj):
        ord_num = Order.objects.filter(user=obj.pk).count()
        return ord_num
    orders.short_description = 'заказы'

    # разработать переход из общего раздела клиент в webaccount, tmaccount


@admin.register(WEBAccount)
class WEBAccountAdmin(UserAdmin):
    """Настройки отображения данных таблицы User."""
    list_display = ('id', 'email', 'is_active', 'is_deleted')
    list_search = ('email', 'is_active', 'first_name', 'last_name', 'phone', )
    list_filter = ('is_active',)
    readonly_fields = ('date_joined', 'last_login')
    fieldsets = (
        ('Основное', {
            'fields': (
                ('first_name', 'last_name'),
                ('is_active', 'is_deleted'),
                ('email', 'phone'),
                ('date_joined', 'last_login'),
                ('is_superuser', 'is_staff'),
                ('web_language')
            )
        }),
        ('Пароль', {
            'fields': (
                ('password'),
            )
        }),
        ('Комментарии', {
            'fields': (
                ('notes'),
            )
        }),
    )
    ordering = ('id',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name',
                       'email', 'phone',
                       'password1', 'password2'),
        }),
    )
