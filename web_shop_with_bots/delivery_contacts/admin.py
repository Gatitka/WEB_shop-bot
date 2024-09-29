from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from parler.admin import TranslatableAdmin
from django.utils.html import format_html
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django import forms
from django.contrib.gis import admin
from django.utils.safestring import mark_safe
from utils.admin_permissions import (has_restaurant_admin_permissions,
                                     has_city_admin_permissions)

from utils.utils import activ_actions

from .models import Delivery, DeliveryZone, Restaurant, Courier


@admin.register(Courier)
class CourierAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_active', 'city', 'name')
    actions = [*activ_actions]
    list_filter = ('is_active', 'city')

    def has_change_permission(self, request, obj=None):
        return has_city_admin_permissions(
            'delivery_contacts.change_couriers',
            request, obj)


@admin.register(Delivery)
class DeliveryAdmin(TranslatableAdmin):
    """Настройки админ панели доставки"."""

    def workhours(self, obj):
        return obj.get_workhours()
    workhours.short_description = 'время выдачи'

    def acctodayhours(self, obj):
        return obj.get_acctodayhours()
    acctodayhours.short_description = format_html(
        "время приема заказов<br>'Сегодня/Как можно быстрее'")

    list_display = ('id', 'is_active', 'city', 'type', 'workhours',
                    'acctodayhours')
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
                ('min_acc_time', 'max_acc_time'),
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

    def has_change_permission(self, request, obj=None):
        return has_city_admin_permissions(
            'delivery_contacts.change_deliveries',
            request, obj)


class DeliveryZoneAdminForm(forms.ModelForm):
    new_polygon_coords = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        label="Новые координаты полигона (WKT)",
        required=False,
        help_text="Введите координаты в формате WKT (Well-Known Text). Пример: "
                  "'MULTIPOLYGON (((x1 y1, x2 y2, ...)))'"
    )

    class Meta:
        model = DeliveryZone
        fields = '__all__'

    def clean_new_polygon_coords(self):
        coords = self.cleaned_data.get('new_polygon_coords')
        if coords:
            try:
                # Преобразуем строку в GEOSGeometry для проверки формата
                geometry = GEOSGeometry(coords)
                if not isinstance(geometry, (Polygon, MultiPolygon)):
                    raise forms.ValidationError("Введите допустимые координаты полигона или мультиполигона.")
            except Exception as e:
                raise forms.ValidationError(f"Ошибка при обработке WKT: {e}")
        return coords


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(OSMGeoAdmin):
    """Настройки админ панели стоимости доставки по районам"."""
    form = DeliveryZoneAdminForm
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
        'polygon_coordinates',
        'new_polygon_coords',
    )
    readonly_fields = ('polygon_coordinates',)

    def polygon_coordinates(self, obj):
        # Здесь вы можете форматировать координаты как вам нужно
        # Например, просто выводить их в строку
        if obj.pk is not None:
            if obj.polygon is not None:
                polygon_str = str(obj.polygon)
                try:
                    polygon_data = polygon_str.split("MULTIPOLYGON (((")[1]
                    return str("MULTIPOLYGON (((" + polygon_data)
                except IndexError:
                    return "нет координат"
        return ''
    polygon_coordinates.short_description = 'WKT координаты полигона'

    def save_model(self, request, obj, form, change):
        # Проверяем, есть ли новые координаты в форме
        new_coords = form.cleaned_data.get('new_polygon_coords')
        if new_coords:
            try:
                # Преобразуем строку в объект GEOSGeometry и сохраняем
                obj.polygon = GEOSGeometry(new_coords)
            except Exception as e:
                self.message_user(request, f"Ошибка при сохранении полигона: {e}", level='error')
        # Сохраняем объект с обновленными данными
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        return has_city_admin_permissions(
            'delivery_contacts.change_delivery_zones',
            request, obj)


@admin.register(Restaurant)
class RestaurantAdmin(OSMGeoAdmin):   # admin.ModelAdmin):
    """Настройки админ панели ресторанов."""

    def acctodayhours(self, obj):
        return obj.get_acctodayhours()
    acctodayhours.short_description = format_html(
        "время приема заказов<br>'Сегодня/Как можно быстрее'")

    default_lat = 44.813366941787976
    default_lon = 20.460647915161385
    default_zoom = 5
    # Beograd 44.813366941787976, 20.460647915161385

    list_display = ('pk', 'city', 'short_name',
                    'is_active', 'phone',
                    'working_hours', 'acctodayhours',
                    'is_overloaded', 'admin_photo', 'is_default')
    readonly_fields = ('admin_photo', 'get_admin')
    list_filter = ('is_active', 'city')
    actions = [*activ_actions]
    fields = (
        ('short_name'),
        ('is_active', 'is_default', 'is_overloaded'),
        ('city'),
        ('address'),
        ('coordinates'),
        ('open_time', 'close_time'),
        ('min_acc_time', 'max_acc_time'),
        ('phone'),
        ('get_admin'),
        ('admin_photo', 'image')
    )

    def working_hours(self, obj):
        return f"{obj.open_time.strftime('%H:%M')} - {obj.close_time.strftime('%H:%M')}"

    working_hours.short_description = 'Рабочие часы'

    def get_admin(self, obj):
        """ Возвращаем админа ресторана."""
        return list(obj.admin.all())
    get_admin.short_description = 'Админы'

    def has_change_permission(self, request, obj=None):
        return has_restaurant_admin_permissions(
            'delivery_contacts.change_restaurant',
            request, obj)
