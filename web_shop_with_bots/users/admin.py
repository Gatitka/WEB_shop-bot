from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.password_validation import validate_password

from shop.models import Order  # ShoppingCart

from .models import BaseProfile, UserAddress, WEBAccount


class UserAddressesAdminInline(admin.TabularInline):
    model = UserAddress
    min_num = 0
    extra = 0   # чтобы не добавлялись путые поля
    fieldsets = (
        ('Адрес', {
            'fields': (
                ('address', 'coordinates',),
                ('flat', 'floor', 'interfon')
            )
        }),
    )



@admin.register(BaseProfile)
class BaseProfileAdmin(admin.ModelAdmin):
    """Настройки отображения данных таблицы User."""
    list_display = ('id', 'is_active', 'first_name', 'last_name',
                    'phone', 'email', 'orders_qty')
    search_fields = ('first_name', 'last_name', 'phone', 'email')
    list_filter = ('is_active',)
    # list_select_related = ['web_account', 'my_addresses']
    ordering = ('id',)
    readonly_fields = ('date_joined', 'orders_qty',
                       'first_name', 'last_name', 'phone', 'email')
    inlines = (UserAddressesAdminInline,)
    raw_id_fields = ['web_account', 'messenger_account']
    fieldsets = (
        ('Основное', {
            'fields': (
                ('first_name', 'last_name', 'phone'),
                ('email', 'web_account', 'messenger_account'),
                ('orders_qty'),
            )
        }),
        ('Дополнительно', {
            'fields': (
                ('is_active', 'date_joined'),
                ('date_of_birth', 'city', 'base_language'),
                ('notes')
            )
        }),
    )

    def get_queryset(self, request):
        qs = BaseProfile.objects.prefetch_related(
            'web_account'
            ).prefetch_related(
                'my_addresses'
                ).all()
        return qs


# разработать переход из общего раздела клиент в webaccount, tmaccount

@admin.register(WEBAccount)
class WEBAccountAdmin(UserAdmin):
    """Настройки отображения данных таблицы User."""
    list_display = ('id', 'email', 'role', 'is_active', 'is_deleted')
    list_search = ('email', 'is_active', 'first_name', 'last_name', 'phone', )
    list_filter = ('is_active', 'role')
    readonly_fields = ('date_joined', 'last_login')
    fieldsets = (
        ('Основное', {
            'fields': (
                ('first_name', 'last_name'),
                ('role', 'is_active', 'is_deleted'),
                ('email', 'phone'),
                ('date_joined', 'last_login'),
                ('is_superuser', 'is_staff'),
                ('is_subscribed'),
                ('web_language')
            )
        }),
        ('Пароль', {
            'fields': (
                ('password'),
            )
        }),
        ('Комментарии', {
            "classes": ["collapse"],
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
