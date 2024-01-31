from django.contrib import admin
from parler.admin import (SortedRelatedFieldListFilter, TranslatableAdmin,
                          TranslatableTabularInline)

from .models import Category, Dish, DishCategory


def make_active(modeladmin, request, queryset):
    """Добавление действия активации выбранных позиций."""
    queryset.update(is_active=1)


def make_deactive(modeladmin, request, queryset):
    """Добавление действия деактивации выбранных позиций."""
    queryset.update(is_active=0)


make_active.short_description = "Отметить позиции активными"
make_deactive.short_description = "Отметить позиции не активными"


class DishCategoryAdmin(admin.TabularInline):
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
    readonly_fields = ('final_price', 'admin_photo', 'created')
    list_display = ('article', 'is_active', 'priority', 'short_name',
                    'price', 'discount', 'final_price',
                    'spicy_icon', 'vegan_icon', 'admin_photo')
    list_filter = ('is_active', 'category__slug',)
    list_per_page = 10

    search_fields = ('translations__short_name__icontains',
                     'translations__text__icontains')
    inlines = (DishCategoryAdmin,)
    actions = [make_active, make_deactive]

    fieldsets = (
        ('Основное', {
            'fields': (
                ('article', 'created'),
                ('is_active', 'priority'),
                ('spicy_icon', 'vegan_icon'),
            )
        }),
        ('Описание', {
            'fields': (
                ('short_name'),
                ('text'),
            )
        }),
        ('Цена', {
            'fields': (
                ('price', 'discount'),
                ('final_price'),
            )
        }),
        ('Характеристики', {
            'fields': (
                ('uom', 'volume', 'weight'),
            )
        }),
        ('Изображение', {
            'fields': ('admin_photo', 'image'),
        })
    )

    # надстройка для увеличения размера текстового поля
    # def formfield_for_dbfield(self, db_field, **kwargs):
    #     if db_field.name == 'text':
    #         kwargs['widget'] = admin.widgets.AdminTextareaWidget(
    #             attrs={'rows': 3, 'cols': 40}
    #             )
    #     return super().formfield_for_dbfield(db_field, **kwargs)

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.db_type == 'text':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(attrs={'rows': 3, 'cols': 40})
        return super().formfield_for_dbfield(db_field, **kwargs)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('translations')


@admin.register(Category)
class CategoryAdmin(TranslatableAdmin):
    """Настройки админ панели категорий."""
    list_display = ('pk', 'priority', 'is_active', 'name', 'slug')
    search_fields = ('translations__name__icontains', 'slug')
    list_filter = ('is_active',)
    actions = [make_active, make_deactive]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('translations')


# @admin.register(Category)
# class CategoryAdmin(admin.ModelAdmin):
#     """Настройки админ панели категорий."""
#     list_display = ('pk', 'priority', 'is_active', 'name_rus', 'slug')
#     search_fields = ('name_rus', 'slug')
#     list_filter = ('is_active',)
#     actions = [make_active, make_deactive]
