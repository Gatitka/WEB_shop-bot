from django.contrib import admin

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
    verbose_name = 'категория'
    verbose_name_plural = 'категории'


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    """Настройки админ панели блюд."""
    readonly_fields = ('final_price_display', 'admin_photo', 'created')
    list_display = ('article', 'is_active', 'priority', 'short_name_rus',
                    'price', 'discount', 'final_price_display',
                    'spicy_icon', 'vegan_icon', 'admin_photo')
    list_filter = ('category', 'is_active',)
    list_per_page = 10

    search_fields = ('short_name_rus', 'text_rus')
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
                ('short_name_rus'),
                ('short_name_srb'),
                ('text_rus'),
                ('text_srb'),
            )
        }),
        ('Цена', {
            'fields': (
                ('price', 'discount'),
                ('final_price_display'),
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

    def final_price_display(self, obj):
        return obj.final_price
    final_price_display.short_description = 'Итоговая цена, DIN'
    final_price_display.admin_order_field = 'Итоговая цена, DIN'

    # надстройка для увеличения размера текстового поля
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'text_rus':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(
                attrs={'rows': 3, 'cols': 40}
                )
        if db_field.name == 'text_srb':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(
                attrs={'rows': 3, 'cols': 40}
                )
        return super().formfield_for_dbfield(db_field, **kwargs)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Настройки админ панели категорий."""
    list_display = ('pk', 'priority', 'is_active', 'name_rus', 'slug')
    search_fields = ('name_rus', 'slug')
    list_filter = ('is_active',)
    actions = [make_active, make_deactive]
