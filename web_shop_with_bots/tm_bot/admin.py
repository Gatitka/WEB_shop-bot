from django.contrib import admin
from django.utils.html import format_html
from .admin_utils import export_tm_accounts_to_excel
from .models import Message, MessengerAccount, OrdersBot, AdminChatTM
from shop.models import Order
from shop.admin_utils import custom_source, custom_order_number
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
    list_display = ('id', 'msngr_type', 'city', 'source_id')
    # form = OrdersBotForm

    # def get_form(self, request, obj=None, **kwargs):
    # НУЖНО ДЛЯ МАСКИРОВКИ ПОЛЯ С АПИ КЛЮЧЕМ, НЕДОДЕЛАНО
    #     form = super().get_form(request, obj, **kwargs)
    #     form.current_user = request.user  # Передаем текущего пользователя в форму
    #     return form

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
              'status', 'delivery', 'recipient_address',
              'final_amount_with_shipping']
    readonly_fields = ['custom_source', 'custom_order_number',
                       'status', 'delivery', 'recipient_address',
                       'final_amount_with_shipping']

    def custom_source(self, obj):
        return custom_source(obj)
    custom_source.short_description = 'Источник'

    def custom_order_number(self, obj):
        return custom_order_number(obj)
    custom_order_number.short_description = '№'


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
    list_display = ('msngr_type', 'msngr_id', 'msngr_username',
                    'get_msngr_link', 'custom_registered',
                    'created', 'get_order_qty')
    readonly_fields = ('get_msngr_link', 'created', 'msngr_link',
                       'get_orders_data', 'get_order_qty')
    list_filter = ('msngr_type', 'subscription', 'registered')
    list_display_links = ('msngr_id',)
    list_per_page = 10
    search_fields = ('msngr_id', 'msngr_username',
                     'msngr_first_name', 'msngr_last_name',
                     'msngr_phone')
    actions = (export_tm_accounts_to_excel,)
    inlines = [OrderInline,]

    fieldsets = (
        ('Основное', {
            'fields': (
                ('msngr_type', 'language', 'created'),
                ('msngr_username', 'get_msngr_link'),
                ('msngr_first_name', 'msngr_last_name'),
                ('notes'),
                ('subscription', 'registered'),
                ('get_orders_data'),
            )
        }),
        ('Дополнительно', {
            "classes": ["collapse"],
            'fields': (
                ('msngr_phone'),
                ('msngr_link'),
                ('msngr_id',),
                ('tm_chat_id'),

            )
        })
    )

    def get_msngr_link(self, instance):
        if instance.msngr_link:
            return format_html(instance.msngr_link)
        return ''
    get_msngr_link.short_description = 'Перейти в чат'

    def get_orders_data(self, instance):
        return instance.get_orders_data()
        #return "временно не доступно"

    get_orders_data.allow_tags = True
    get_orders_data.short_description = 'Всего заказов через бот'
