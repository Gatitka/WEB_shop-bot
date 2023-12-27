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
    min_num = 1
    verbose_name = 'категория'
    verbose_name_plural = 'категория'


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    """Настройки админ панели блюд."""
    fields = (('article', 'is_active', 'priority'),
              ('short_name_rus', 'short_name_srb'),
              ('text_rus', 'text_srb'),
              ('price', 'discount'),
              ( 'final_price'),
              ('uom', 'volume', 'weight'),
              ('spicy_icon', 'vegan_icon'),
              )
    readonly_fields = ('final_price',)
    list_display = ('pk', 'is_active', 'priority', 'short_name_rus',
                    'price', 'discount', 'final_price',
                    'spicy_icon', 'vegan_icon')
                    #  image preview
    list_filter = ('category', 'is_active',)
    search_fields = ('short_name_rus', 'text_rus')
    inlines = (DishCategoryAdmin,)
    actions = [make_active, make_deactive]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Настройки админ панели категорий."""
    list_display = ('pk', 'priority', 'is_active', 'name_rus', 'slug') # URL
    search_fields = ('name_rus', 'slug')
    list_filter = ('is_active',)
    actions = [make_active, make_deactive]
