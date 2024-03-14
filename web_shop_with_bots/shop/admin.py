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
from delivery_contacts.utils import google_validate_address_and_get_coordinates
from delivery_contacts.services import get_delivery_zone
from django.core.exceptions import ValidationError
from shop.validators import validate_delivery_time


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
    readonly_fields = ['amount', 'unit_price', 'dish_article', 'cart_number',]
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
        js = ('my_admin/js/shop/cartitem_data_admin_request.js',)

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
    readonly_fields = ['amount', 'unit_price', 'dish_article', 'order_number']
    verbose_name = 'товар заказа'
    verbose_name_plural = 'товары заказа'
    # raw_id_fields = ['dish',]
    autocomplete_fields = ['dish']

    # def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
    #     return super().get_queryset(request).select_related('dish').prefetch_related('dish__translations')


class OrderAdminForm(forms.ModelForm):
    recipient_address = forms.CharField(
               required=False,
               widget=forms.TextInput(attrs={'size': '40',
                                             'autocomplete': 'on',
                                             'class': 'basicAutoComplete',
                                             'style': 'width: 50%;'}))
    class Meta:
        model = Order
        fields = '__all__'

    def clean_recipient_address(self):
        delivery = self.cleaned_data.get('delivery')
        recipient_address = self.cleaned_data.get('recipient_address')

        if delivery is not None and delivery.type == 'delivery':

            if recipient_address is None or recipient_address == '':
                raise forms.ValidationError(
                    "Проверьте указан ли адрес доставки клиенту.")

            if recipient_address != self.instance.recipient_address:

                try:
                    lat, lon, status = google_validate_address_and_get_coordinates(
                        recipient_address
                    )
                    self.lat = lat
                    self.lon = lon

                except Exception as e:
                    pass
                #     if (self.cleaned_data.get('delivery_zone') is None
                #         or self.cleaned_data.get('delivery_cost') is None):

                #         raise forms.ValidationError(
                #             ("Ошибка в получении координат адреса, невозможно "
                #                 "посчитать стоимость доставки."
                #                 "Проверьте адрес или внесите вручную зону доставки и цену.")
                #         )

        return recipient_address

    def clean_delivery_zone(self):
        delivery = self.cleaned_data.get('delivery')
        delivery_zone = self.cleaned_data.get('delivery_zone')

        if delivery is not None and delivery.type == 'delivery':
            recipient_address = self.cleaned_data.get('recipient_address')
            if recipient_address != self.instance.recipient_address:

                if delivery_zone is None:
                    try:
                        new_delivery_zone = get_delivery_zone(
                            self.cleaned_data.get('city', 'Beograd'),
                            self.lat, self.lon)
                        if new_delivery_zone.name == 'уточнить':
                            raise forms.ValidationError(
                                ("Введенный адрес находится вне зоны обслуживания."
                                "Проверьте адрес или внесите вручную зону и цену доставки.")
                            )
                    except AttributeError:
                        raise forms.ValidationError(
                                ("Для введенного адреса невозможно получить координаты "
                                "и расчитать зону доставки. Проверьте адрес или внесите "
                                "вручную зону и цену доставки.")
                            )

                elif delivery_zone.name in ['zone1', 'zone2', 'zone3',
                                            'по запросу', 'уточнить']:
                    try:
                        new_delivery_zone = get_delivery_zone(
                            self.cleaned_data.get('city', 'Beograd'),
                            self.lat, self.lon)
                        if new_delivery_zone.name == 'уточнить':
                            raise forms.ValidationError(
                                ("Введенный адрес находится вне зоны обслуживания."
                                "Проверьте адрес или внесите вручную зону и цену доставки.")
                            )
                    except AttributeError:
                        raise forms.ValidationError(
                                ("Для введенного адреса невозможно получить координаты "
                                "и расчитать зону доставки. Проверьте адрес или внесите "
                                "вручную зону и цену доставки.")
                            )

                    if delivery_zone != new_delivery_zone:
                        return new_delivery_zone

        return delivery_zone

    def clean_delivery_cost(self):
        delivery = self.cleaned_data.get('delivery')
        delivery_cost = self.cleaned_data.get('delivery_cost')

        if delivery is not None and delivery.type == 'delivery':
            delivery_zone = self.cleaned_data.get('delivery_zone')
            if delivery_zone and delivery_zone.name == 'по запросу':

                if delivery_cost is None or delivery_cost == 0.0:
                    raise forms.ValidationError(
                        ("Для зоны доставки 'по запросу' необходимо "
                         "внести вручную стоимость доставки.")
                    )
        return delivery_cost

    def clean_delivery_time(self):
        delivery = self.data.get('delivery')
        delivery_time = self.cleaned_data.get('delivery_time')
        restaurant = self.cleaned_data.get('restaurant')

        if delivery_time is not None and delivery is not None:
            delivery = Delivery.objects.filter(id=int(delivery)).first()

            if delivery.type == 'takeaway' and restaurant is not None:
                validate_delivery_time(delivery_time, delivery, restaurant)
            else:
                validate_delivery_time(delivery_time, delivery)

        return delivery_time

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Используем сохраненные значения lat и lon из атрибутов формы
        recipient_address = self.cleaned_data.get('recipient_address')
        if recipient_address != self.instance.recipient_address:
            instance.delivery_address_data = {
                "lat": self.lat,
                "lon": self.lon
            }

        if commit:
            instance.save()

        return instance


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Настройки админ панели заказов.
    ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""
    def custom_order_number(self, obj):
        # краткое название поля в list
        return obj.order_number
    custom_order_number.short_description = '№'

    def custom_status(self, obj):
        # краткое название поля в list
        return obj.status
    custom_status.short_description = 'стат'

    def custom_language(self, obj):
        # краткое название поля в list
        return obj.language
    custom_language.short_description = 'lg'

    def custom_recipient_name(self, obj):
        # краткое название поля в list
        return obj.recipient_name
    custom_recipient_name.short_description = format_html('Имя<br>получателя')

    def custom_recipient_phone(self, obj):
        # краткое название поля в list
        return obj.recipient_phone
    custom_recipient_phone.short_description = format_html('Тел<br>получателя')

    def custom_total(self, obj):
        # краткое название поля в list
        return obj.final_amount_with_shipping
    custom_total.short_description = format_html('Сумма<br>заказа, DIN')

    def custom_is_first_order(self, obj):
        # краткое название поля в list
        if obj.is_first_order:
            return '+'
        return ''
    custom_is_first_order.short_description = format_html('Перв<br>заказ')

    def custom_created(self, obj):
        # Преобразование поля datetime в строку с помощью strftime()
        return format_html(obj.created.strftime('%H:%M<br>%Y.%m.%d'))
    custom_created.short_description = 'создан'

    def warning(self, obj):
        # Преобразование поля datetime в строку с помощью strftime()
        if obj.delivery.type == 'delivery' and obj.delivery_zone.name == 'уточнить':
            return '!!!'
        return ''
    warning.short_description = '!'
    list_display = ('warning', 'custom_is_first_order',
                    'custom_order_number', 'custom_created', 'custom_status',
                    'custom_language',
                    'custom_recipient_name', 'custom_recipient_phone',
                    'get_msngr_link',
                    'delivery', 'recipient_address',
                    'custom_total', 'id')
    list_display_links = ('custom_order_number',)
    readonly_fields = ['discounted_amount',
                       'items_qty', 'device_id', 'amount',
                       'final_amount_with_shipping',
                       'get_msngr_link']
    list_filter = ('created', 'status') # user_groups, paid
    search_fields = ('user', 'order_number')
    inlines = (OrderDishInline,)
    raw_id_fields = ['user',]
    actions_selection_counter = False   # Controls whether a selection counter is displayed next to the action dropdown. By default, the admin changelist will display it
    list_per_page = 10
    radio_fields = {"payment_type": admin.HORIZONTAL,
                    "delivery": admin.HORIZONTAL}

    fieldsets = (
        ('Данные заказа', {
            'fields': (
                ('status', 'language'),
                ('user', 'device_id'),
                ('city', 'restaurant'),
                ('recipient_name', 'recipient_phone', 'get_msngr_link'),
                ('delivery_time', 'persons_qty'),
                ('delivery'),
            )
        }),
        ('Доставка', {
            # "classes": ["collapse"],
            "description": "Заполните 'адрес' для автоматического расчета зоны доставки и стоимости.",
            'fields': (
                ('recipient_address'),
                ('delivery_address_data'),
                ('delivery_zone'),
                ('delivery_cost'),
            )
        }),
        ('Расчет суммы заказа', {
            'fields': (
                ('amount'),
                ('promocode', 'discount'),
                ('discounted_amount'),
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
    # add_form_template = 'order/my_order_change_add_form.html'
    change_form_template = 'order/change_form.html'

    class Media:
        js = (# 'my_admin/js/shop/google_key_window.js',
              'my_admin/js/shop/google_key_check.js',
              'my_admin/js/shop/address_autocomplete.js',)

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
        extra_context["GOOGLE_API_KEY"] = self.get_google_api_key()
        # self.change_form_template = 'order/change_form.html'
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
        return super().add_view(
            request,
            form_url,
            extra_context=extra_context
        )

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)

        if db_field.name == 'delivery':
            formfield.required = True

        elif db_field.name == 'recipient_address':
            kwargs['widget'] = admin.widgets.AdminTextInputWidget(
                attrs={'rows': 1, 'cols': 100,
                       'autocomplete': 'on'})
            formfield.required = False

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
    get_msngr_link.short_description = 'Чат'
