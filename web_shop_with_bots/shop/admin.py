from decimal import Decimal
from typing import Any, Mapping, Union

from django import forms
from django.contrib import admin
from django.core.files.base import File
from django.db.models import Sum
from django.db.models.base import Model
from django.db.models.query import QuerySet
from django.forms.utils import ErrorList
from django.http.request import HttpRequest
from django.utils import formats
from django.utils.html import format_html

from tm_bot.models import MessengerAccount
from users.models import BaseProfile
from utils.utils import activ_actions

from .models import CartDish, Order, OrderDish, ShoppingCart
from users.models import UserAddress

admin.site.register(OrderDish)
admin.site.register(CartDish)


class ShopAdminArea(admin.AdminSite):
    site_header = 'YUME Shop Admin'
    login_template = 'shop/admin/login.html'

shop_site = ShopAdminArea(name='ShopAdmin')
shop_site.register(Order)

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
    readonly_fields = ['amount', 'unit_price']
    autocomplete_fields = ['dish']

    verbose_name = 'товары корзины'
    verbose_name_plural = 'товары корзин'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('dish__translations', 'cart__user__messenger_account')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    """Настройки админ панели карзины.
    ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""
    list_display = ('pk', 'complited', 'user',
                    'created', 'discounted_amount')
    readonly_fields = ['created', 'discounted_amount',
                       'device_id', 'amount', 'discount', 'items_qty']
    list_filter = ('created', 'complited')
    raw_id_fields = ['user', ]
    inlines = (CartDishInline,)
    fields = (('created', 'complited'),
              ('user', 'device_id'),
              ('items_qty', 'amount'),
              ('promocode', 'discount'),
              ('discounted_amount'),
              )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).prefetch_related('user')

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
        total_amount = CartDish.objects.filter(
                cart=shopping_cart
                    ).aggregate(ta=Sum('amount'))
        shopping_cart.amount = (Decimal(total_amount['ta']) if total_amount['ta'] is not None
                                else Decimal(0))
        shopping_cart.save(update_fields=['amount', 'discounted_amount'])

        formset.save_m2m()


class OrderDishInline(admin.TabularInline):
    """Вложенная админка OrderDish для добавления товаров в заказ (создания записей OrderDish)
    сразу в админке заказа (через объект Order)."""
    model = OrderDish
    min_num = 0
    extra = 0   # чтобы не добавлялись путые поля
    readonly_fields = ['amount', 'unit_price',]
    verbose_name = 'заказ'
    verbose_name_plural = 'заказы'
    # raw_id_fields = ['dish',]
    autocomplete_fields = ['dish']

    # def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
    #     return super().get_queryset(request).select_related('dish').prefetch_related('dish__translations')


class OrderAdminForm(forms.ModelForm):

    class Meta:
        model = Order
        fields = '__all__'

    def clean_recipient_address(self):
        delivery_value = self.cleaned_data.get('delivery')
        recipient_address = self.cleaned_data.get('recipient_address')
        if delivery_value == 'delivery' and not recipient_address:
            raise forms.ValidationError("Recipient address is required for delivery.")
        return recipient_address

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.db_type == 'text':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(
                attrs={'rows': 3, 'cols': 40}
            )
        return super().formfield_for_dbfield(db_field, **kwargs)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Настройки админ панели заказов.
    ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""
    list_display = ('pk', 'status',
                    'recipient_name', 'recipient_phone', 'get_msngr_link',
                    'created', 'delivery', 'recipient_address',
                    'final_amount_with_shipping')
    readonly_fields = ['pk', 'created', 'discounted_amount',
                       'items_qty', 'device_id', 'amount',
                       'final_amount_with_shipping',
                       'get_msngr_link',]
    list_filter = ('created', 'status') # user_groups, paid
    search_fields = ('user', 'pk')
    inlines = (OrderDishInline,)
    raw_id_fields = ['user',]
    actions_selection_counter = False   # Controls whether a selection counter is displayed next to the action dropdown. By default, the admin changelist will display it
    list_per_page = 10

    fieldsets = (
        ('Данные заказа', {
            'fields': (
                ('pk', 'created'),
                ('status'),
                ('user', 'device_id'),
                ('restaurant', 'delivery'),
                ('recipient_name', 'recipient_phone', 'get_msngr_link'),
                ('time', 'persons_qty'),
            )
        }),
        ('Доставка', {
            'fields':
                ('city', 'recipient_address')
        }),
        ('Расчет суммы заказа', {
            'fields': (
                ('amount'),
                ('promocode', 'discount'),
                ('discounted_amount'),
                ('delivery_cost'),
            )
        }),
        ('ИТОГО', {
            'fields': (
                ('final_amount_with_shipping'),
                ('items_qty'),
            )
        }),
        ('Комментарий', {
            'fields': ('comment',),
        })
    )

    form = OrderAdminForm

    def get_queryset(self, request):
        qs = super().get_queryset(
            request
            ).select_related(
                'user',
                'delivery',
                'user__messenger_account')

        return qs

    def get_object(self, request: HttpRequest, object_id: str, from_field: None = ...) -> Union[Any, None]:
        queryset = super().get_queryset(
            request
            ).select_related(
                'delivery',
                'promocode',
                'restaurant'
            ).prefetch_related(
                'user',
                'user__messenger_account')
        return super().get_object(request, object_id, from_field)

# ------ ОТОБРАЖЕНИЕ ССЫЛКИ НА ЧАТ С КЛИЕНТОМ -----

    def get_msngr_link(self, instance):
        try:
            return format_html(instance.user.messenger_account.msngr_link)
        except:
            return None

        if MessengerAccount.objects.filter(profile=instance.user).exists():
            return format_html(instance.user.messenger_account.msngr_link)


    get_msngr_link.allow_tags = True
    get_msngr_link.short_description = 'Ссылка в Telegram'
