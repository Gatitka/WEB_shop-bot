from django.contrib import admin
from django.utils.html import format_html
from .admin_utils import export_tm_accounts_to_excel
from .models import Message, MessengerAccount, OrdersBot, AdminChatTM, MessengerAccountBot
from .admin_filters import Bot1WriteFilter, Bot2WriteFilter
from shop.models import Order
from shop.admin_utils import custom_source, get_custom_order_number
from django_admin_inline_paginator.admin import TabularInlinePaginated
from django import forms
from utils.admin_permissions import (has_restaurant_admin_permissions,
                                     has_city_admin_permissions)

# @admin.register(Message)
# class MessageAdmin(admin.ModelAdmin):
#     """Настройки отображения данных таблицы Message."""
#     list_display = ('id', 'profile', 'text', 'created_at')
#     list_filter = ('profile',)


# class OrdersBotForm(forms.ModelForm):
#     api_key = forms.CharField(
#         widget=forms.PasswordInput(render_value=True),  # Можно задать виджет прямо в поле
#         required=False
#     )

#     class Meta:
#         model = OrdersBot
#         fields = '__all__'

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         if not self.current_user.is_superuser:
#             if 'api_key' in self.fields:
#                 self.fields['api_key'].widget = forms.PasswordInput(render_value=True)  # Маскирует символы


@admin.register(OrdersBot)
class OrdersBotAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'msngr_type', 'admin_id')
    search_fields = ('name', 'city', 'source_id')
    change_form_template = 'tm_bot/ordersbot/change_form.html'
    list_display_links = ('name',)
    fieldsets = (
        ('Основное', {
            'fields': (
                ('name', 'is_active'),
                ('city', 'msngr_type'),
                ('link'),
                ('frontend_link')
            )
        }),
        ('Админ', {
            "description": (
                "Данные админа, для тестовых рассылок. Если ID админа пуст, "
                "то тестовая промо-рассылка не прийдет."
            ),
            'fields': (
                ('admin_username'),
                ('admin_id'),
            )
        }),
        ('Привязка к платформам', {
            "classes": ["collapse"],
            "description": (
                "Если бот привязан к платформе-конструктуру ботов, "
                "то тут вносятся учетные данные с той платформы:<br>"
                "- API ключ (если необходима верификация API запросов)<br>"
                "- ID на платформе (прим. Botobot)<br>"
            ),
            'fields': (
                ('api_key'),
                ('source_id'),
            )
        }),
    )

    def get_chart_data(self, obj):
        links = MessengerAccountBot.objects.filter(bot=obj)

        can_write = links.filter(tg_can_write=True).count()

        blocked = links.filter(
            tg_can_write=False,
            last_error_code="403_bot_blocked"
        ).count()

        deactivated = links.filter(
            tg_can_write=False,
            last_error_code="403_user_deactivated"
        ).count()

        chat_not_found = links.filter(
            tg_can_write=False,
            last_error_code="400_chat_not_found"
        ).count()

        unknown = links.filter(tg_can_write__isnull=True).count()

        return {
            'can_write': can_write,
            'cannot_write': blocked + deactivated,
            'chat_not_found': chat_not_found,
            'unknown': unknown,
            'total': links.count(),
        }

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Добавляем данные для диаграммы в контекст."""
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj:
            extra_context['chart_data'] = self.get_chart_data(obj)
        return super().change_view(request, object_id, form_url, extra_context)

    def has_change_permission(self, request, obj=None):
        return has_city_admin_permissions(
            'tm_bot.change_ordersbot',
            request, obj)


@admin.register(AdminChatTM)
class AdminChatTMAdmin(admin.ModelAdmin):
    list_display = ('id', 'city', 'restaurant', 'chat_id')

    def has_change_permission(self, request, obj=None):
        return has_restaurant_admin_permissions(
            'tm_bot.change_adminchat',
            request, obj)


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


class MessengerAccountBotInline(admin.TabularInline):
    model = MessengerAccountBot
    extra = 0
    fields = ("bot", "tg_can_write", "last_login",
              "last_success_at", "last_error_at", "last_error_code")
    readonly_fields = (
        "bot", "last_login",
        "last_success_at", "last_error_at", "last_error_code")
    # autocomplete_fields = ("bot",)  # удобно, если ботов много

    # чтобы нельзя было случайно удалять связки (по желанию)
    can_delete = False


@admin.register(MessengerAccount)
class MessagerAccountAdmin(admin.ModelAdmin):
    def custom_registered(self, obj):
        if obj.registered:
            return '✅'
        return ''
    custom_registered.short_description = format_html(
                                            'Регистрация<br>на сайте')

    def get_order_qty(self, obj):
        if hasattr(obj, 'orders'):
            orders_qty = obj.orders.count()
        else:
            orders_qty = 0
        return orders_qty
    get_order_qty.short_description = 'Зак'

    """Настройки отображения данных таблицы Message."""
    list_display = ('id', 'msngr_type', 'msngr_id', 'msngr_username',
                    'get_msngr_link', 'custom_registered',
                    'created', 'get_order_qty')
    readonly_fields = ('get_msngr_link', 'created',
                       'get_orders_data', 'get_order_qty')
    list_filter = ('msngr_type', 'subscription', 'registered', 'city',
                   Bot1WriteFilter, Bot2WriteFilter)
    list_display_links = ('msngr_id',)
    list_per_page = 10
    search_fields = ('id',
                     'msngr_id', 'msngr_username',
                     'msngr_first_name', 'msngr_last_name',
                     'msngr_phone')
    actions = (export_tm_accounts_to_excel,)
    inlines = [MessengerAccountBotInline, OrderInline,]

    fieldsets = (
        ('Основное', {
            'fields': (
                ('msngr_type', 'msngr_id'),
                ('msngr_username', 'get_msngr_link'),
                ('msngr_first_name', 'msngr_last_name'),
                ('subscription', 'registered', 'city'),
                ('language', 'created'),
                ('notes'),
                ('get_orders_data'),
            )
        }),
        ('Дополнительно', {
            "classes": ["collapse"],
            'fields': (
                ('msngr_phone'),
                ('msngr_link'),
                ('tm_chat_id'),

            )
        })
    )

    def get_msngr_link(self, instance):
        if instance.msngr_link:
            return format_html(instance.msngr_link)
        return format_html(
            "<span style='color:#888;'>"
            "Чат недоступен<br>нет username (Telegram)<br>или телефона (WhatsApp)."
            "</span>"
        )
    get_msngr_link.short_description = 'Перейти в чат'

    def get_orders_data(self, instance):
        return instance.get_orders_data()
        #return "временно не доступно"

    get_orders_data.allow_tags = True
    get_orders_data.short_description = 'Всего заказов через бот'
