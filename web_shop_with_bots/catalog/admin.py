from django.contrib import admin
from django.utils.html import format_html
from parler.admin import TranslatableAdmin, TranslatableTabularInline
from .models import (UOM, Category, Dish, DishCategory,
                     RestaurantDishList, CityDishList)
from django.contrib.admin.views.decorators import staff_member_required
from utils.admin_permissions import (
    has_restaurant_orders_admin_permissions,
    has_city_orders_admin_permissions)
from django.db.models import Prefetch


def make_active(modeladmin, request, queryset):
    """Добавление действия активации выбранных позиций."""
    queryset.update(is_active=1)


def make_deactive(modeladmin, request, queryset):
    """Добавление действия деактивации выбранных позиций."""
    queryset.update(is_active=0)


make_active.short_description = "Отметить позиции активными"
make_deactive.short_description = "Отметить позиции не активными"

# admin.site.register(DishCategory)


class DishCategoryInlineAdmin(admin.TabularInline):
    """Вложенная админка DishCategory для добавления категори блюда
    сразу в админке блюда (через объект Dish)."""
    model = DishCategory
    min_num = 0
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('dish__translations')


@admin.register(Dish)
class DishAdmin(TranslatableAdmin):
    """Настройки админ панели блюд."""
    def custom_vegan_icon(self, obj):
        # краткое название поля в list
        if obj.vegan_icon is False:
            return '-'
        return '+'
    custom_vegan_icon.short_description = format_html('остр<br>икн')

    def custom_spicy_icon(self, obj):
        # краткое название поля в list
        if obj.spicy_icon is False:
            return '-'
        return '+'
    custom_spicy_icon.short_description = format_html('остр<br>икн')

    readonly_fields = ('id', 'final_price', 'admin_photo', 'created')
    list_display = ('id', 'article', 'is_active', 'priority', 'short_name',
                    'discount', 'final_price',
                    'custom_spicy_icon', 'custom_vegan_icon')   # 'admin_photo')
    list_filter = ('is_active', 'category__slug',)
    list_per_page = 10

    search_fields = ('translations__short_name__icontains',
                     'translations__text__icontains')
    inlines = (DishCategoryInlineAdmin,)
    actions = [make_active, make_deactive]
    list_select_related = False
    list_display_links = ('article',)

    fieldsets = (
        ('Основное', {
            'fields': (
                ('article'),
                ('id', 'created'),
                ('is_active', 'priority'),
                ('spicy_icon', 'vegan_icon'),
            )
        }),
        ('Тексты для сайта', {
            'fields': (
                ('short_name'),
                ('text'),
            )
        }),
        ('Тексты для мессенджера', {
            'fields': (
                ('msngr_short_name'),
                ('msngr_text'),
            )
        }),
        ('Цена', {
            'fields': (
                ('price', 'discount'),
                ('final_price'),
                ('final_price_p1'),
                ('final_price_p2'),
            )
        }),
        ('Характеристики', {
            'fields': (
                ('weight_volume', 'weight_volume_uom',),
                ('units_in_set', 'units_in_set_uom'),
                ('utensils')
            )
        }),
        ('Изображение', {
            'fields': ('admin_photo', 'image'),
        })
    )

    # надстройка для увеличения размера текстового поля
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in ['short_name', 'text',
                             'msngr_short_name', 'msngr_text']:
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(
                attrs={'rows': 3, 'cols': 40}
            )
        return super().formfield_for_dbfield(db_field, **kwargs)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('translations')

    # def get_object(self, request, object_id, from_field=None):
    #     """
    #     Customized get_object method to retrieve the object with select_related and prefetch_related.
    #     """
    #     # Customize the queryset with select_related and prefetch_related
    #     queryset = self.get_queryset(request)
    #     queryset = queryset.select_related('weight_volume_uom', 'units_in_set_uom')
    #     queryset = queryset.prefetch_related('weight_volume_uom__translations',
    #                                          'units_in_set_uom__translations')

    #     # Retrieve the object based on the object_id
    #     obj = queryset.get(article=object_id)

    #     return obj

    # def get_search_results(self, request, queryset, search_term):
    #     queryset, may_have_duplicates = super().get_search_results(
    #         request,
    #         queryset,
    #         search_term,
    #     )

    #     queryset |= self.model.objects.filter(translations__short_name__icontains=search_term)
    #     return queryset, may_have_duplicates


@admin.register(Category)
class CategoryAdmin(TranslatableAdmin):
    """Настройки админ панели категорий."""
    list_display = ('pk', 'priority', 'is_active', 'name', 'slug')
    search_fields = ('translations__name__icontains', 'slug')
    list_filter = ('is_active',)
    actions = [make_active, make_deactive]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('translations')


@admin.register(UOM)
class UOMAdmin(TranslatableAdmin):

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('translations')


@admin.register(RestaurantDishList)
class RestaurantDishAdmin(admin.ModelAdmin):
    filter_horizontal = ('dish',)

    # def get_queryset(self, request):
    #     queryset = super().get_queryset(request).select_related(
    #         'restaurant'
    #     ).prefetch_related(
    #         Prefetch('dish',
    #                  queryset=Dish.objects.prefetch_related('translations'))
    #     )
    #     return queryset

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return super().has_change_permission(request)

        return has_restaurant_orders_admin_permissions(request,
                                                       obj)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "dish":
            # Подгружаем все блюда с переводами сразу, если это необходимо
            kwargs["queryset"] = Dish.objects.all().prefetch_related('translations')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(CityDishList)
class CityDishListAdmin(admin.ModelAdmin):
    filter_horizontal = ('dish',)    # Виджет для удобного управления ManyToMany связью

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return super().has_change_permission(request)

        return has_city_orders_admin_permissions(request,
                                                 obj)
