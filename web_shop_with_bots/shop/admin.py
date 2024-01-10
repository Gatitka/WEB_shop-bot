from typing import Any
from django.contrib import admin
from django.utils import formats
from .models import ShoppingCart, CartDish, Order, OrderDish
from users.models import BaseProfile
from utils.utils import activ_actions
from django.db.models import Sum
from decimal import Decimal
from django import forms


# admin.site.register(OrderDish)
# admin.site.register(CartDish)


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
                       'num_of_items', 'device_id', 'amount']
    list_filter = ('created', 'complited')
    # raw_id_fields = ['user', ]
    inlines = (CartDishInline,)
    fields = (('formatted_created', 'complited'),
              ('user', 'device_id'),
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

# ------ настройки оптимизации сохранения CartDish из inline -----
    def save_related(self, request, form, formsets, change):
        '''
        Метод кастомизирован для
        оптимизации сохранения связаного объекта ShoppingCart.
        При стандартном подходе, сохранение CartDish вызывается методом save(),
        который тригерит пересохранение итоговых значений Shopping cart:
        amount / final amount.
        Сейчас внесен кастомный метод save_in_flow,
        который не пересохраняет Shopping Cart каждый раз.
        Данные ShoppingCart финалятся и пересохраняются в конце этого метода.
        '''
        form.save_m2m()

        for formset in formsets:
            if formset.model == CartDish:

                # Пересохраняем formset для:
                #   - добавления instances, "макеты" экземпляров
                # класса CartDish, заполненные в формах
                # !!!!(все - новые, измененные, удаленные)
                #   - добавление новых списков:
                # new_objects, changed_objects, deleted_objects
                instances = formset.save(commit=False)
                # если commit=True, то экземпляры сохранятся стандартным
                # методом save, тригеря каждый раз пересохранение корзины
                # сейчас пересохранение итоговых сумм делается в конце данного метода

                for instance in instances:
                    instance.save_in_flow()    # данный метод сохранения не обновляет итоговые суммы всей корзины
                if hasattr(formset, 'deleted_objects') and formset.deleted_objects:
                    for deleted_object in formset.deleted_objects:
                        deleted_object.delete()

        shopping_cart = form.instance
        total_amount = Decimal(
            CartDish.objects.filter(
                cart=shopping_cart
                    ).aggregate(ta=Sum('amount'))['ta']
            )
        shopping_cart.amount = (total_amount if total_amount is not None
                                else Decimal(0))
        shopping_cart.save(update_fields=['amount', 'final_amount'])

        formset.save_m2m()


class OrderDishInline(admin.TabularInline):
    """Вложенная админка OrderDish для добавления товаров в заказ (создания записей OrderDish)
    сразу в админке заказа (через объект Order)."""
    model = OrderDish
    min_num = 0
    extra = 0   # чтобы не добавлялись путые поля
    readonly_fields = ['amount']
    verbose_name = 'заказ'
    verbose_name_plural = 'заказы'


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Настройки админ панели заказов.
    ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""
    list_display = ('pk', 'status',
                    'recipient_name', 'recipient_phone',
                    'formatted_created', 'delivery',
                    'discounted_amount', 'final_amount_with_shipping')
    readonly_fields = ['pk', 'formatted_created', 'discounted_amount',
                       'num_of_items', 'device_id', 'amount',
                       'final_amount_with_shipping']
    list_filter = ('created', 'status') # user_groups, paid
    search_fields = ('user', 'pk')
    inlines = (OrderDishInline,)

    # def user_phone(self, obj):
    #     return BaseProfile.objects.get(id=obj.user_id).phone
    # user_phone.short_description = 'Телефон'
    fieldsets = (
        ('Данные заказа',{
            'fields': (
                ('pk', 'formatted_created'),
                ('status'),
                ('user', 'device_id'),
                ('shop', 'delivery'),
                ('recipient_name', 'recipient_phone'),
                ('time', 'persons_qty'),
            )
        }),
        ('Доставка',{
            'fields':
                ('recipient_district', 'recipient_address')
        }),
        ('Сумма заказа',{
            'fields': (
                ('amount'),
                ('promocode', 'discount'),
                ( 'discounted_amount'),
                ('delivery_cost'),
                ('final_amount_with_shipping', 'num_of_items'),
            )
        }),
        ('Комментарий',{
            'fields': ('comment',),
        })
    )


    form = OrderAdminForm

    def get_form(self, request, obj=None, **kwargs):
        form = super(OrderAdmin, self).get_form(request, obj, **kwargs)

        # Динамически устанавливаем атрибут required для полей recipient_district и recipient_address
        if 'delivery' in form.base_fields:
            delivery_value = request.POST.get('delivery') if request.method == 'POST' else getattr(obj, 'delivery', None)
            if delivery_value == '1':
                form.base_fields['recipient_district'].required = True
                form.base_fields['recipient_address'].required = True
            else:
                form.base_fields['recipient_district'].required = False
                form.base_fields['recipient_address'].required = False

        return form


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
