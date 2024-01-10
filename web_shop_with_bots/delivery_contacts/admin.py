from django.contrib import admin
from .models import Delivery, Shop, DistrictDeliveryCost
from utils.utils import activ_actions


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    """Настройки админ панели доставки".
    ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""
    list_display = ('name_rus', 'type', 'city', 'is_active', 'min_price', 'price')
    search_fields = ('name_rus', 'city')
    list_filter = ('is_active', 'city', 'type')
    actions = [*activ_actions]


@admin.register(DistrictDeliveryCost)
class DistrictDeliveryCostAdmin(admin.ModelAdmin):
    """Настройки админ панели стоимости доставки по районам"."""
    list_display = ('city', 'district', 'promo', 'min_order_amount', 'delivery_cost')
    search_fields = ('district', 'city')
    list_filter = ('city', 'promo')
    actions = [*activ_actions]


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """Настройки админ панели магазинов."""
    list_display = ('pk', 'city', 'short_name', 'is_active', 'phone', 'work_hours')
    search_fields = ('city', 'short_name', 'phone')
    list_filter = ('is_active', 'city')
    actions = [*activ_actions]
