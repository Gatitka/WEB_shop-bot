from django.contrib import admin
# from shop.models import Favorit

from .models import Category, Dish   # DishIngredient, Ingredient


def make_active(modeladmin, request, queryset):
    """Добавление действия активации выбранных позиций."""
    queryset.update(active=1)


def make_deactive(modeladmin, request, queryset):
    """Добавление действия деактивации выбранных позиций."""
    queryset.update(active=0)


make_active.short_description = "Отметить позиции активными"
make_deactive.short_description = "Отметить позиции не активными"


# class DishIngredientAdmin(admin.TabularInline):
#     """Вложенная админка DishIngredient для добавления ингредиентов в блюдо (DishIngredient)
#     сразу в админке блюда (через объект Dish)."""
#     model = DishIngredient
#     min_num = 1
#     verbose_name = 'ингридиент'
#     verbose_name_plural = 'ингридиенты'


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    """Настройки админ панели блюд."""
    fields = (('article', 'active'),
              'category',
              ('short_name_rus', 'short_name_srb'),
              ('text_rus', 'text_srb'),
              ('price', 'uom', 'volume', 'weight')
              )
    list_display = ('pk', 'active', 'short_name_rus',
                    'category', 'price')  #'in_favorits', image preview
    list_filter = ('category', 'active',)
    search_fields = ('short_name_rus',)
    # inlines = (DishIngredientAdmin,)
    actions = [make_active, make_deactive]

    # def in_favorits(self, obj):
    #     return Favorit.objects.filter(dish=obj).count()
    # in_favorits.short_description = 'В избранном'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Настройки админ панели категорий."""
    list_display = ('pk', 'priority', 'active', 'name_rus', 'slug') # URL
    search_fields = ('name_rus',)
    actions = [make_active, make_deactive]


# @admin.register(Ingredient)
# class IngredientAdmin(admin.ModelAdmin):
#     """Настройки отображения данных таблицы Ingredient."""
#     list_display = ('pk', 'name_rus', 'measurement_unit')
#     list_filter = ('name_rus',)
