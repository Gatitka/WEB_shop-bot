from django.contrib import admin

from .models import (ShoppingCart, CartDish, Order, OrderDish, Delivery, Shop)
# from users.models import BaseProfile
from utils.utils import activ_actions


class CartDishInline(admin.TabularInline):
    """Вложенная админка CartDish для добавления товаров в заказ (создания записей CartDish)
    сразу в админке заказа (через объект Cart)."""
    model = CartDish
    min_num = 1
    readonly_fields = ['amount']
    verbose_name = 'товары корзины'
    verbose_name_plural = 'товары корзин'


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    """Настройки админ панели карзины.
    ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""
    list_display = ('pk', 'complited', 'user',
                    'created', 'num_of_items', 'total_amount')
    readonly_fields = ['total_amount', 'num_of_items']
    list_filter = ('user', 'created', 'complited')
    inlines = (CartDishInline,)


class OrderDishInline(admin.TabularInline):
    """Вложенная админка OrderDish для добавления товаров в заказ (создания записей OrderDish)
    сразу в админке заказа (через объект Order)."""
    model = OrderDish
    min_num = 1
    readonly_fields = ['amount']
    verbose_name = 'заказ'
    verbose_name_plural = 'заказы'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Настройки админ панели заказов.
    ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""
    list_display = ('pk', 'status',
                    'user', 'recipient_phone',
                    'created', 'delivery',
                    'total_amount')
    readonly_fields = ['total_amount']
    list_filter = ('status', 'user', 'created') # user_groups, paid
    inlines = (OrderDishInline,)

    # def user_phone(self, obj):
    #     return BaseProfile.objects.get(id=obj.user_id).phone
    # user_phone.short_description = 'Телефон'


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    """Настройки админ панели доставки".
    ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""
    list_display = ('name_rus', 'type', 'is_active', 'min_price', 'price')
    actions = [*activ_actions]


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """Настройки админ панели магазинов."""
    list_display = ('pk', 'short_name', 'is_active', 'phone', 'work_hours')
    actions = [*activ_actions]
