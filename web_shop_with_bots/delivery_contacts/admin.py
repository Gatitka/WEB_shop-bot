from django.contrib import admin
from .models import Delivery, Shop, DistrictDeliveryCost
from utils.utils import activ_actions


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    """Настройки админ панели доставки".
    ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""
    list_display = ('name_rus', 'type', 'city',
                    'is_active', 'min_price', 'price', 'admin_photo')
    readonly_fields = ('admin_photo',)
    search_fields = ('name_rus', 'city')
    list_filter = ('is_active', 'city', 'type')
    actions = [*activ_actions]

    fieldsets = (
        ('Основное', {
            'fields': (
                ('type', 'is_active'),
                ('city')
            )
        }),
        ('Описание', {
            'fields': (
                ('name_rus'),
                ('name_srb'),
                ('name_en'),
                ('description_rus'),
                ('description_srb'),
                ('description_en'),
            )
        }),
        ('Цена', {
            'fields': (
                ('price', 'min_price'),
                ('discount'),
            )
        }),
        ('Изображение', {
            'fields': ('admin_photo', 'image'),
        })
    )


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
    list_display = ('pk', 'city', 'short_name',
                    'is_active', 'phone', 'work_hours', 'admin_photo')
    readonly_fields = ('admin_photo',)
    search_fields = ('city', 'short_name', 'phone')
    list_filter = ('is_active', 'city')
    actions = [*activ_actions]
    fields = (
        ('short_name', 'is_active'),
        ('city'),
        ('address_rus'),
        ('address_end'),
        ('address_srb'),
        ('work_hours'),
        ('phone'),
        ('admin'),
        ('admin_photo', 'image')
    )
