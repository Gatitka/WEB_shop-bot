from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.password_validation import validate_password
from django.utils.html import format_html
from .models import BaseProfile, UserAddress, WEBAccount
from django.urls import reverse
from .forms import BaseProfileAdminForm
from shop.models import Order
from shop.admin_utils import custom_source, get_custom_order_number
from django_admin_inline_paginator.admin import TabularInlinePaginated
from audit.models import AuditLog
from rangefilter.filters import NumericRangeFilter
from django.contrib.auth.models import Group


class UserAddressesAdminInline(admin.TabularInline):
    model = UserAddress
    min_num = 0
    extra = 0   # чтобы не добавлялись путые поля
    classes = ['collapse']
    fieldsets = (
        ('Адрес', {
            'fields': (
                ('city', 'address', 'coordinates',),
                ('flat', 'floor', 'interfon')
            )
        }),
    )


class OrderInline(TabularInlinePaginated):
    model = Order
    extra = 0  # Не добавлять пустые строки для новых заказов
    per_page = 5
    fields = ['custom_source', 'custom_order_number',
              'status', 'delivery', 'recipient_address',
              'final_amount_with_shipping']
    readonly_fields = ['custom_source', 'custom_order_number',
                       'status', 'delivery', 'recipient_address',
                       'final_amount_with_shipping']

    def custom_source(self, obj):
        return custom_source(obj)
    custom_source.short_description = 'Источник'

    def custom_order_number(self, obj):
        return get_custom_order_number(obj)
    custom_order_number.short_description = '№'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ActionsInline(TabularInlinePaginated):
    model = AuditLog
    extra = 0  # Не добавлять пустые строки для новых заказов
    per_page = 5
    classes = ['collapse']
    fields = ['id', 'created', 'status',
              'action', 'details']
    readonly_fields = ['id', 'created', 'status',
                       'action', 'details']

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Фильтрация действий по профилю пользователя
        if hasattr(self, 'parent_obj'):
            qs = qs.filter(user__base_profile=self.parent_obj)
        return qs

    def get_formset(self, request, obj=None, **kwargs):
        self.parent_obj = obj
        return super().get_formset(request, obj, **kwargs)


@admin.register(BaseProfile)
class BaseProfileAdmin(admin.ModelAdmin):

    def full_name(self, obj):
        return format_html('{}<br>{}',
                           obj.first_name, obj.last_name)
    full_name.allow_tags = True
    full_name.short_description = 'Имя Фамилия'

    def get_contacts(self, obj):
        lang = obj.get_flag()
        phone = obj.phone if obj.phone else ''
        return format_html('{}<br>{}<br>{}',
                           lang, phone, obj.email)
    get_contacts.allow_tags = True
    get_contacts.short_description = 'Контакты'

    def custom_orders_qty(self, obj):
        return obj.orders_qty
    custom_orders_qty.short_description = 'Зак'

    def custom_first_web_order(self, obj):
        if obj.orders_qty:
            return '✅'
        return ''
    custom_first_web_order.short_description = format_html(
        '1й заказ<br>на сайте')

    """Настройки отображения данных таблицы User."""
    list_display = ('id', 'is_active', 'full_name',
                    'get_contacts', 'messenger_account', 'custom_orders_qty',
                    'custom_first_web_order', 'date_joined')
    search_fields = ('first_name', 'last_name', 'phone', 'email')
    list_filter = ('is_active',
                   ('orders_qty', NumericRangeFilter),
                   'web_account__role')
    # list_select_related = ['web_account', 'my_addresses']
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'orders_qty', 'get_orders_data',
                       'first_name', 'last_name', 'phone', 'email',
                       'get_is_subscribed', 'get_city')
    inlines = (OrderInline,
               UserAddressesAdminInline,
               ActionsInline)
    raw_id_fields = ['web_account', 'messenger_account']
    list_per_page = 10
    list_display_links = ['full_name']
    form = BaseProfileAdminForm
    fieldsets = (
        ('Основное', {
            "description": (
                "Для изменения личных клиента кликните на его e-mail.<br><br>"
                "<b>ТАМ</b> можно изменить:<br>"
                "- Имя, Фамилия, Телефон, e-mail, выбранный язык<br>"
                "- включить/выключить подписку<br>"
                "- сменить пароль<br>"
                "- активировать/деактивировать нового зарегестрированного пользователя<br>"
                "- поставить отметку об удалении пользователя"

            ),
            'fields': (
                ('first_name', 'last_name', 'phone'),
                ('web_account', 'messenger_account'),
                ('get_city',),
                ('get_orders_data',),
                ('first_web_order',)
            )
        }),
        ('Дополнительно', {
            "classes": ["collapse"],
            'fields': (
                ('is_active', 'date_joined'),
                ('date_of_birth', 'base_language'),
                ('get_is_subscribed',),
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

    def get_orders_data(self, instance):
        return instance.get_orders_data()
        # return "временно не доступно"

    get_orders_data.allow_tags = True
    get_orders_data.short_description = 'Всего заказов'

    def get_city(self, instance):
        return instance.web_account.city
    get_city.allow_tags = True
    get_city.short_description = 'Город'

    def get_is_subscribed(self, instance):
        return instance.web_account.is_subscribed
    get_is_subscribed.allow_tags = True
    get_is_subscribed.short_description = 'Подписка на новости'


class GroupInline(admin.StackedInline):
    model = WEBAccount.groups.through
    extra = 1
    verbose_name = "Группа пользовательских прав доступа"
    verbose_name_plural = "Группы пользовательских прав доступа"


@admin.register(WEBAccount)
class WEBAccountAdmin(UserAdmin):
    """Настройки отображения данных таблицы User."""
    list_display = ('id', 'email', 'role', 'is_active', 'is_deleted')
    list_search = ('email', 'is_active', 'first_name', 'last_name', 'phone', )
    list_filter = ('is_active', 'role')
    list_per_page = 10
    ordering = ('id',)
    readonly_fields = ('date_joined', 'last_login')
    search_fields = ('first_name', 'last_name', 'phone', 'email')
    # inlines = (GroupInline,)
    fieldsets = (
        ('Основное', {
            'fields': (
                ('first_name', 'last_name'),
                ('is_active', 'is_deleted'),
                ('city', 'email', 'phone'),
                ('date_joined', 'last_login'),
                ('role', 'is_superuser', 'is_staff', 'restaurant'),
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
        ('Права пользователя и группы допуска', {
            "classes": ["collapse"],
            'fields': (
                ('groups',),
                ('user_permissions',)
            )
        })
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name',
                       'email', 'phone',
                       'password1', 'password2'),
        }),
    )

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}

    def get_form(self, request, obj=None, **kwargs):
        """
        Переопределяем метод get_form для передачи пользователя в форму.
        """
        form = super().get_form(request, obj, **kwargs)
        is_superuser = request.user.is_superuser

        if not is_superuser:
            form.base_fields['is_superuser'].disabled = True
            form.base_fields['user_permissions'].disabled = True
            form.base_fields['groups'].disabled = True
            form.base_fields['role'].disabled = True
            form.base_fields['restaurant'].disabled = True
            form.base_fields['is_staff'].disabled = True
        if obj and obj != request.user and obj.is_staff:
            form.base_fields['email'].disabled = True
            form.base_fields['is_active'].disabled = True
            form.base_fields['is_deleted'].disabled = True
        return form
