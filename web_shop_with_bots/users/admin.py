from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django_admin_inline_paginator.admin import TabularInlinePaginated
from rangefilter.filters import NumericRangeFilter

from audit.models import AuditLog
from shop.models import Order
from shop.admin_utils import custom_source, get_custom_order_number
from .admin_actions import total_user_delete
from .forms import BaseProfileAdminForm, WEBAccountAdminForm
from .models import BaseProfile, UserAddress, WEBAccount


class UserAddressInlineForm(forms.ModelForm):
    class Meta:
        model = UserAddress
        fields = "__all__"
        widgets = {
            "city": forms.Select(attrs={"style": "width: 140px;"}),
            "address": forms.TextInput(attrs={"style": "width: 420px;"}),
            "coordinates": forms.TextInput(attrs={"style": "width: 260px;"}),
            "flat": forms.TextInput(attrs={"style": "width: 120px;"}),
            "floor": forms.TextInput(attrs={"style": "width: 120px;"}),
            "interfon": forms.TextInput(attrs={"style": "width: 120px;"}),
        }


class UserAddressesAdminInline(admin.StackedInline):
    model = UserAddress
    form = UserAddressInlineForm
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
              'status', 'custom_delivery', 'recipient_address',
              'final_amount_with_shipping']
    readonly_fields = ['custom_source', 'custom_order_number',
                       'status', 'custom_delivery', 'recipient_address',
                       'final_amount_with_shipping']

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('delivery', 'restaurant')  # убирает N+1 по ресторану и доставке
        )

    def custom_source(self, obj):
        label = custom_source(obj)  # "TM_Bot", "Wolt" и т.п.
        url = obj.get_admin_url()
        return format_html("<a href='{}'>{}</a>", url, label)
    custom_source.short_description = 'Источник'

    def custom_order_number(self, obj):
        return get_custom_order_number(obj)
    custom_order_number.short_description = '№'

    def custom_delivery(self, obj):
        return str(obj.delivery)
    custom_delivery.short_description = 'Доставка'

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
        if hasattr(self, 'parent_obj'):
            qs = qs.filter(user__base_profile=self.parent_obj)
        return qs.select_related('user')  # убирает повторный джойн на webaccount

    def get_formset(self, request, obj=None, **kwargs):
        self.parent_obj = obj
        return super().get_formset(request, obj, **kwargs)


@admin.register(BaseProfile)
class BaseProfileAdmin(admin.ModelAdmin):

    def full_name(self, obj):
        if obj.first_name or obj.last_name:
            return format_html('{}<br>{}',
                               obj.first_name, obj.last_name)
        else:
            return "Не заполнено"
    full_name.allow_tags = True
    full_name.short_description = 'Имя Фамилия'

    def get_contacts(self, obj):
        lang = obj.get_flag()
        phone = obj.phone if obj.phone else ''
        email = obj.email if "example.invalid" not in obj.email else ''
        return format_html('{}<br>{}<br>{}',
                           lang, phone, email)
    get_contacts.allow_tags = True
    get_contacts.short_description = 'Контакты'

    def custom_orders_qty(self, obj):
        return obj.orders_qty
    custom_orders_qty.short_description = 'Зак'

    def date_joined_short(self, obj):
        if obj.date_joined:
            return obj.date_joined.strftime("%d.%m.%Y")  # без времени
        return "—"
    date_joined_short.short_description = format_html('Дата<br>регистрации')

    def get_last_login(self, obj):
        web_last_login = getattr(obj.web_account, "last_login", None)

        tm_last_login = None
        ma = getattr(obj, "messenger_account", None)
        if ma:
            # берём самый свежий last_login среди всех bot_links
            bot_links = getattr(ma, "_prefetched_objects_cache", {}).get("bot_links")
            if bot_links is None:
                bot_links = ma.bot_links.all()

            tm_values = [link.last_login for link in bot_links if link.last_login]
            if tm_values:
                tm_last_login = max(tm_values)

        candidates = []
        if web_last_login:
            candidates.append(("WEB", web_last_login))
        if tm_last_login:
            candidates.append(("Tm", tm_last_login))

        if not candidates:
            return "—"

        login_type, dt = max(candidates, key=lambda x: x[1])
        local_dt = timezone.localtime(dt)

        return format_html(
            "{} ({})<br>{}",
            local_dt.strftime("%d.%m.%Y"),
            login_type,
            local_dt.strftime("%H:%M"),
        )
    get_last_login.short_description = format_html('Последний<br>логин')

    """Настройки отображения данных таблицы User."""
    list_display = ('id', 'is_active', 'full_name',
                    'get_contacts', 'get_msngr_link', 'custom_orders_qty',
                    'date_joined_short', 'get_last_login')
    search_fields = ('first_name', 'last_name', 'phone', 'email',
                     'messenger_account__msngr_username',
                     'messenger_account__msngr_id')
    list_filter = ('is_active',
                   ('orders_qty', NumericRangeFilter),
                   'web_account__role',
                   'messenger_account__msngr_type',
                   'web_account__city',
                   'web_account__auth_via')
    # list_select_related = ['web_account', 'my_addresses']
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'orders_qty', 'get_orders_data',
                       'first_name', 'last_name', 'phone', 'email',
                       'get_is_subscribed', 'get_city', 'get_msngr_link',
                       'get_last_login')
    inlines = (OrderInline,
               UserAddressesAdminInline,
               ActionsInline)
    raw_id_fields = ['web_account', 'messenger_account']
    list_per_page = 10
    list_display_links = ['full_name']
    actions = [total_user_delete] if settings.DEBUG else []
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
                ('first_name', 'last_name', 'get_city'),
                ('phone', 'get_msngr_link'),
                ('web_account', 'messenger_account'),
                ('get_orders_data',),
                ('first_web_order',)
            )
        }),
        ('Дополнительно', {
            "classes": ["collapse"],
            'fields': (
                ('is_active', 'date_joined', 'get_last_login'),
                ('date_of_birth', 'base_language'),
                ('get_is_subscribed',),
                ('notes')
            )
        }),
    )

    def get_queryset(self, request):
        # qs = BaseProfile.objects.prefetch_related(
        #     'web_account'
        #     ).prefetch_related(
        #         'my_addresses'
        #     ).select_related(
        #         "messenger_account"
        #         ).all()
        # return qs
        return (
            BaseProfile.objects
            .select_related("web_account", "messenger_account", "my_addresses")
            .prefetch_related("messenger_account__bot_links")
        )

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

    def get_msngr_link(self, instance):
        try:
            if instance.messenger_account:
                if instance.messenger_account.msngr_link:
                    return format_html(instance.messenger_account.msngr_link)
                return format_html(
                    "<span style='color:#888;'>"
                    "Чат недоступен<br>нет username (Telegram)<br>или телефона (WhatsApp)."
                    "</span>"
                )
            return format_html(
                    "<span style='color:#888;'>"
                    "нет мессенджера</span>"
                )
        except:
            return format_html(
                "<span style='color:#888;'>"
                "Чат недоступен<br></span>"
            )

    get_msngr_link.allow_tags = True
    get_msngr_link.short_description = 'Перейти в чат'

    def get_actions(self, request):
        # убираем только удаление, чтобы никто не мог удалить
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class GroupInline(admin.StackedInline):
    model = WEBAccount.groups.through
    extra = 1
    verbose_name = "Группа пользовательских прав доступа"
    verbose_name_plural = "Группы пользовательских прав доступа"

from django.contrib.contenttypes.models import ContentType

@admin.register(WEBAccount)
class WEBAccountAdmin(UserAdmin):
    """Настройки отображения данных таблицы User."""
    form = WEBAccountAdminForm
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
