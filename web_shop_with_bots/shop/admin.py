from typing import Any
from django.contrib import admin
from django.utils import formats
from .models import ShoppingCart, CartDish, Order, OrderDish
from users.models import BaseProfile
from utils.utils import activ_actions
from django.db.models import Sum


admin.site.register(OrderDish)
admin.site.register(CartDish)


# @admin.register(BaseProfile)
# class BaseProfileFieldSearchAdmin(admin.ModelAdmin):
#     list_display = [
#         'id'
#     ]
#     search_fields = ['id']


class CartDishInline(admin.TabularInline):
    """
    Вложенная админка CartDish для добавления товаров в заказ
    (создания записей CartDish) сразу в админке заказа (через объект Cart).
    """
    model = CartDish
    min_num = 0
    extra = 0   # чтобы не добавлялись путые поля
    readonly_fields = ['amount']
    verbose_name = 'товары корзины'
    verbose_name_plural = 'товары корзин'


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    """Настройки админ панели карзины.
    ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""
    list_display = ('pk', 'complited', 'user',
                    'formatted_created', 'num_of_items', 'final_amount')
    readonly_fields = ['formatted_created', 'final_amount',
                       'num_of_items', 'session_id', 'amount']
    list_filter = ('created', 'complited')
    # raw_id_fields = ['user', ]
    inlines = (CartDishInline,)
    fields = (('formatted_created', 'complited'),
              ('user', 'session_id'),
              ('num_of_items', 'amount'),
              ('promocode', 'discount'),
              ('final_amount'),
              )

# ------ настройки для формата даты -----
    def formatted_created(self, obj):
        # Форматируем дату в нужный вид
        formatted_date = formats.date_format(obj.created, "j F Y, H:i")
        return formatted_date

    formatted_created.short_description = 'Дата добавления'
    # Название колонки в админке

    # Если нужно применить формат в деталях объекта
    def changeform_view(self, request, object_id=None, form_url='',
                        extra_context=None):
        extra_context = extra_context or {}
        extra_context['admin_date_formats'] = {
            'formatted_created': "j F Y, H:i"
            }
        return super().changeform_view(request, object_id, form_url, extra_context)

    def save_related(self, request, form, formsets, change):
        # super().save_related(request, form, formsets, change)
        form.save_m2m()
        # Получаем сохраненный экземпляр ShoppingCart
        shopping_cart = form.instance

        # Теперь вы можете обновить связанные CartDish

        for formset in formsets:
            if formset.model == CartDish:
                for cart_dish_form in formset.forms:
                    cart_dish = cart_dish_form.instance

                    # Проверяем, были ли объекты помечены для удаления
                    if not cart_dish_form.cleaned_data.get('DELETE'):
                        quantity = cart_dish_form.cleaned_data.get('quantity', 0)
                        dish = cart_dish_form.cleaned_data.get('dish')

                        # Обновляем данные объекта CartDish
                        cart_dish.quantity = quantity
                        cart_dish.dish = dish
                        cart_dish.save_in_flow()


    #     # for formset in formsets:
    #     #     if formset.model == CartDish:
    #     #         # Проверяем, были ли объекты помечены для удаления
    #     #         # if hasattr(formset, 'deleted_objects') and formset.deleted_objects:
    #     #         #     for deleted_object in formset.deleted_objects:
    #     #         #         deleted_object.delete()
    #     #         for cart_dish_form in formset.forms:
    #     #             cart_dish = cart_dish_form.instance

    #     #             # Вы можете получить данные из формы и использовать их
    #     #             # для обновления связанных объектов CartDish
    #     #             if not cart_dish_form.cleaned_data.get('DELETE'):
    #     #                 quantity = cart_dish_form.cleaned_data.get('quantity', 0)
    #     #                 dish = cart_dish_form.cleaned_data.get('dish')

    #     #                 # Обновляем данные объекта CartDish
    #     #                 cart_dish.quantity = quantity
    #     #                 cart_dish.dish = dish
    #     #                 # cart_dish.amount = dish.final_price * quantity
    #     #                 cart_dish.save_in_flow()

        total_amount = CartDish.objects.filter(cart=shopping_cart).aggregate(ta=Sum('amount'))['ta']
        shopping_cart.amount = total_amount if total_amount is not None else 0
        shopping_cart.save(update_fields=['amount', 'final_amount'])




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
                    'amount')
    readonly_fields = ['amount']
    list_filter = ('status', 'created') # user_groups, paid
    search_fields = ('user', 'pk')
    inlines = (OrderDishInline,)

    # def user_phone(self, obj):
    #     return BaseProfile.objects.get(id=obj.user_id).phone
    # user_phone.short_description = 'Телефон'
