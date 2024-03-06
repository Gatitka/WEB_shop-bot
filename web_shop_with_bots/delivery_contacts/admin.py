from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin

from utils.utils import activ_actions

from .models import Delivery, DeliveryZone, Restaurant
from parler.admin import TranslatableAdmin


@admin.register(Delivery)
class DeliveryAdmin(TranslatableAdmin):
    """Настройки админ панели доставки".
    ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""
    list_display = ('id', 'is_active', 'city', 'type')
    readonly_fields = ('admin_photo',)
    list_filter = ('is_active', 'city', 'type')
    actions = [*activ_actions]

    fieldsets = (
        ('Основное', {
            'fields': (
                ('type', 'is_active'),
                ('city'),
                ('min_order_amount'),
                ('min_time', 'max_time'),
            )
        }),
        ('Доставка', {
            'fields': (
                ('default_delivery_cost'),
            )
        }),
        ('Самовывоз', {
            'fields': (
                ('discount'),
            )
        }),
        ('Описание', {
            'fields': (
                ('description'),
            )
        }),
        ('Изображение', {
            'fields': ('admin_photo', 'image'),
        })
    )

    # надстройка для увеличения размера текстового поля
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.db_type == 'text':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(attrs={'rows': 1, 'cols': 40})
        return super().formfield_for_dbfield(db_field, **kwargs)


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(OSMGeoAdmin):
    """Настройки админ панели стоимости доставки по районам"."""
    list_display = ('name', 'city', 'is_promo',
                    'promo_min_order_amount', 'delivery_cost',
                    )
    search_fields = ('district', 'city')
    list_filter = ('city', 'is_promo')
    actions = [*activ_actions]
    fields = (
        'city',
        'name',
        'polygon',
        'is_promo',
        'promo_min_order_amount',
        'delivery_cost',
        'polygon_coordinates'
    )
    readonly_fields = ('polygon_coordinates',)

    def polygon_coordinates(self, obj):
        # Здесь вы можете форматировать координаты как вам нужно
        # Например, просто выводить их в строку
        if obj.pk is not None:
            polygon_str = str(obj.polygon)
            polygon_data = polygon_str.split("MULTIPOLYGON (((")[1]
            return str("MULTIPOLYGON (((" + polygon_data)
    polygon_coordinates.short_description = 'WKT координаты полигона'


@admin.register(Restaurant)
class RestaurantAdmin(OSMGeoAdmin):   # admin.ModelAdmin):
    """Настройки админ панели ресторанов."""
    default_lat = 44.813366941787976
    default_lon = 20.460647915161385
    default_zoom = 5
    # Beograd 44.813366941787976, 20.460647915161385

    list_display = ('pk', 'city', 'short_name',
                    'is_active', 'phone',
                    'working_hours',
                    'is_overloaded', 'admin_photo', 'is_default')
    readonly_fields = ('admin_photo',)
    list_filter = ('is_active', 'city')
    actions = [*activ_actions]
    fields = (
        ('short_name', 'is_active'),
        ('is_overloaded', 'is_default'),
        ('city'),
        ('address'),
        ('coordinates'),
        ('open_time', 'close_time'),
        ('phone'),
        ('admin'),
        ('admin_photo', 'image')
    )

    def working_hours(self, obj):
        return f"{obj.open_time.strftime('%H:%M')} - {obj.close_time.strftime('%H:%M')}"

    working_hours.short_description = 'Рабочие часы'
