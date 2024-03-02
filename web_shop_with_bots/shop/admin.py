from decimal import Decimal
from typing import Any, Union

from django import forms
from django.contrib import admin
from django.db.models import Sum
from django.db.models.query import QuerySet
from django.forms.utils import ErrorList
from django.http.request import HttpRequest
from django.utils import formats
from django.utils.html import format_html

from tm_bot.models import MessengerAccount
from users.models import BaseProfile
from utils.utils import activ_actions
from delivery_contacts.models import Delivery

from .models import CartDish, Order, OrderDish, ShoppingCart
from users.models import UserAddress
from django.conf import settings


if settings.ENVIRONMENT == 'development':
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
    min_num = 1   # хотя бы 1 блюдо должно быть добавлено
    extra = 0   # чтобы не добавлялись путые поля
    readonly_fields = ['amount', 'unit_price', 'dish_article', 'cart_number', 'base_profile']
    autocomplete_fields = ['dish']

    verbose_name = 'товар корзины'
    verbose_name_plural = 'товары корзины'

    # class Media:
    #     js = ('js/shop/admin/cartitem_data_admin_request.js',)

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
    change_form_template = 'admin/shop/shoppingcart/my_shoping_cart_change_form.html'

    class Media:
        js = ('js/shop/admin/cartitem_data_admin_request.js',)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).prefetch_related('user')

    # def save_model(self, request, obj, form, change):
    #     from django.contrib import messages
    #     from django.utils.html import format_html
    #     if change:
    #         # Если объект уже существует и редактируется
    #         messages.warning(request, format_html(
    #             '<div style="display: flex; flex-direction: column;">'
    #             'Вы уверены, что хотите сохранить изменения?'
    #             '<button style="margin-top: 10px;" type="submit" name="_continue" value="Save and continue editing" class="default">Да</button>'
    #             '<button style="margin-top: 10px;" type="submit" name="_save" value="Save" class="default">Сохранить</button>'
    #             '<button style="margin-top: 10px;" type="button" class="cancel-button">Нет</button>'
    #             '</div>'
    #         ))
    #     else:
    #         # Если объект создается
    #         messages.info(request, format_html(
    #             '<div style="display: flex; flex-direction: column;">'
    #             'Вы уверены, что хотите сохранить объект?'
    #             '<button style="margin-top: 10px;" type="submit" name="_continue" value="Save and continue editing" class="default">Да</button>'
    #             '<button style="margin-top: 10px;" type="submit" name="_save" value="Save" class="default">Сохранить</button>'
    #             '<button style="margin-top: 10px;" type="button" class="cancel-button">Отменить</button>'
    #             '</div>'
    #         ))


class OrderDishInline(admin.TabularInline):
    """Вложенная админка OrderDish для добавления товаров в заказ (создания записей OrderDish)
    сразу в админке заказа (через объект Order)."""
    model = OrderDish
    min_num = 1   # хотя бы 1 блюдо должно быть добавлено
    extra = 0   # чтобы не добавлялись путые поля
    fields = ['dish', 'quantity', 'unit_price', 'amount']
    readonly_fields = ['amount', 'unit_price', 'dish_article', 'order_number', 'base_profile']
    verbose_name = 'товар заказа'
    verbose_name_plural = 'товары заказа'
    # raw_id_fields = ['dish',]
    autocomplete_fields = ['dish']

    # def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
    #     return super().get_queryset(request).select_related('dish').prefetch_related('dish__translations')


class OrderAdminForm(forms.ModelForm):
    recipient_address = forms.CharField(
               widget=forms.TextInput(attrs={'size': '40',
                                             'autocomplete': 'on',
                                             'class': 'basicAutoComplete'}))

    class Meta:
        model = Order
        fields = '__all__'

    def clean_recipient_address(self):
        delivery = self.cleaned_data.get('delivery')
        recipient_address = self.cleaned_data.get('recipient_address')
        if (delivery is not None and delivery.type == 'delivery') and (
                recipient_address is None or recipient_address == ''):
            raise forms.ValidationError("Проверьте указан ли адрес доставки клиенту.")
        return recipient_address

    def clean(self):
        cleaned_data = super().clean()
        delivery = cleaned_data.get('delivery')
        if not delivery:
            raise forms.ValidationError("Выберите способ доставки.")
        return cleaned_data



@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Настройки админ панели заказов.
    ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""
    list_display = ('order_number', 'status', 'language',
                    'recipient_name', 'recipient_phone', 'get_msngr_link',
                    'created', 'delivery', 'recipient_address',
                    'final_amount_with_shipping')
    readonly_fields = ['order_number', 'created', 'discounted_amount',
                       'items_qty', 'device_id', 'amount',
                       'final_amount_with_shipping',
                       'get_msngr_link',]
    list_filter = ('created', 'status') # user_groups, paid
    search_fields = ('user', 'order_number')
    inlines = (OrderDishInline,)
    raw_id_fields = ['user',]
    actions_selection_counter = False   # Controls whether a selection counter is displayed next to the action dropdown. By default, the admin changelist will display it
    list_per_page = 10
    radio_fields = {"payment_type": admin.HORIZONTAL}
                    #"delivery": admin.HORIZONTAL}

    fieldsets = (
        ('Данные заказа', {
            'fields': (
                ('order_number', 'created'),
                ('status', 'language'),
                ('user', 'device_id'),
                ('city', 'restaurant'),
                ('recipient_name', 'recipient_phone', 'get_msngr_link'),
                ('time', 'persons_qty'),
                ('delivery'),
            )
        }),
        ('Доставка', {
            'classes': ['wide'],
            'fields':
                ('recipient_address',)
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
                ('payment_type'),
            )
        }),
        ('Комментарий', {
            'fields': ('comment',),
        })
    )

    form = OrderAdminForm
    add_form_template = 'admin/shop/order/my_order_change_form.html'
    change_form_template = 'admin/shop/order/my_order_change_form.html'

    class Media:
        js = ('js/shop/admin/address_autocomplete.js',)

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

    def get_google_api_key(self):
        return settings.GOOGLE_API_KEY

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        # Добавление ключа API Google Maps в контекст
        extra_context["google_api_key"] = self.get_google_api_key()
        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context=extra_context,
        )

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        # Добавление ключа API Google Maps в контекст
        extra_context["GOOGLE_API_KEY"] = self.get_google_api_key()
        return super(OrderAdmin, self).add_view(
            request,
            form_url,
            extra_context=extra_context,
        )

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)

        if db_field.name == 'delivery':
            formfield.required = True

        elif db_field.name == 'recipient_address':
            kwargs['widget'] = admin.widgets.AdminTextInputWidget(
                attrs={'rows': 1, 'cols': 50,
                       'autocomplete': 'on'})

        #     delivery_value = self.cleaned_data.get('delivery')
        #     if delivery_value:
        #         try:
        #             delivery_obj = Delivery.objects.get(pk=delivery_value)
        #             if delivery_obj.type == 'delivery':
        #                 formfield.required = True
        #         except Delivery.DoesNotExist:
        #             raise forms.ValidationError("Выберите способ доставки.")
        return formfield

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
