from decimal import Decimal
from typing import Any, Union
from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.db.models.query import QuerySet
from django.forms.utils import ErrorList
from django.http.request import HttpRequest
from django.utils import formats, timezone
from django.utils.html import format_html
from delivery_contacts.utils import get_google_api_key
from tm_bot.models import MessengerAccount
from users.models import BaseProfile, UserAddress
from utils.utils import activ_actions
from .forms import OrderAdminForm
from .models import CartDish, Order, OrderDish, ShoppingCart, Discount

if settings.ENVIRONMENT == 'development':
    admin.site.register(OrderDish)
    admin.site.register(CartDish)


admin.site.register(Discount)


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
    # change_form_template = 'admin/shop/shoppingcart/my_shoping_cart_change_form.html'

    # class Media:
    #     js = ('my_admin/js/shop/cartitem_data_admin_request.js',)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).prefetch_related('user')


class OrderDishInline(admin.TabularInline):
    """Вложенная админка OrderDish для добавления товаров в заказ (создания записей OrderDish)
    сразу в админке заказа (через объект Order)."""
    model = OrderDish
    min_num = 1   # хотя бы 1 блюдо должно быть добавлено
    extra = 0   # чтобы не добавлялись путые поля
    fields = ['dish', 'quantity', 'unit_price', 'amount']
    readonly_fields = ['dish_widget', 'amount', 'unit_price', 'dish_article', 'order_number']
    verbose_name = 'товар заказа'
    verbose_name_plural = 'товары заказа'
    # raw_id_fields = ['dish',]
    autocomplete_fields = ['dish']

    def dish_widget(self, instance):
        return instance.dish  # Замените на соответствующее поле блюда

    dish_widget.short_description = 'Dish'



    # def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
    #     return super().get_queryset(request).select_related('dish').prefetch_related('dish__translations')


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
        if obj.status == 'WCO':
            return format_html(
                '<span style="color:green; font-weight:bold;">{}</span>',
                obj.status)
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

        local_time = obj.created.astimezone(timezone.get_current_timezone())
        if obj.status == 'WCO':
            formatted_time = local_time.strftime('%H:%M')
            formatted_time = format_html(
                '<span style="color:green;font-weight:bold;">{}</span>',
                formatted_time)
        else:
            formatted_time = local_time.strftime('%H:%M')
        return format_html(formatted_time)
    custom_created.short_description = 'создан'

    def warning(self, obj):
        # Преобразование поля datetime в строку с помощью strftime()
        if obj.delivery.type == 'delivery' and obj.delivery_zone.name == 'уточнить':
            return format_html('<span style="color:red;">!!!</span>')
        return ''
    warning.short_description = '!'

    def custom_delivery(self, obj):
        # краткое название поля в list
        if obj.delivery.type == 'delivery':
            return 'D'
        elif obj.delivery.type == 'takeaway':
            return 'T'
    custom_delivery.short_description = 'Дост'

    def custom_delivery_zone(self, obj):
        # краткое название поля в list
        if obj.delivery.type == 'delivery':
            if obj.delivery_zone.name == 'уточнить':
                return format_html('<span style="color:red;">уточн</span>')
            return obj.delivery_zone
        return ''
    custom_delivery_zone.short_description = format_html('зона')

    custom_delivery_zone.short_description = format_html('зона')

    list_display = ('warning', 'custom_is_first_order',
                    'custom_order_number', 'custom_created', 'custom_status',
                    'custom_language',
                    'custom_recipient_name', 'get_contacts',
                    'custom_delivery', 'custom_delivery_zone',
                    'recipient_address',
                    'custom_total', 'id')
    list_display_links = ('custom_order_number',)
    readonly_fields = ['discounted_amount',
                       'items_qty', 'device_id', 'amount',
                       'final_amount_with_shipping',
                       'get_msngr_link',]
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
            "classes": ["collapse"],
            "description": "Заполните 'адрес' для автоматического расчета зоны доставки и стоимости.",
            'fields': (
                ('recipient_address'),
                ('my_recipient_address'),
                ('address_coordinates'),
                ('delivery_address_data'),
                ('calculate_delivery_button'),
                ('auto_delivery_zone', 'delivery_zone'),
                ('auto_delivery_cost', 'delivery_cost'),
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
    add_form_template = 'order/change_form.html'
    change_form_template = 'order/change_form.html'

    class Media:
        js = (
              'my_admin/js/shop/address_autocomplete.js',
              'my_admin/js/shop/user_data.js',
              'my_admin/js/shop/calculate_delivery.js',
              )

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

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        # Добавление ключа API Google Maps в контекст
        extra_context["GOOGLE_API_KEY"] = get_google_api_key()
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
        extra_context["GOOGLE_API_KEY"] = get_google_api_key()
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

    def get_contacts(self, instance):
        try:
            msngr_link = format_html(instance.user.messenger_account.msngr_link)
        except:
            msngr_link = '-'

        return format_html('{}<br>{}', instance.recipient_phone, msngr_link)

        # if MessengerAccount.objects.filter(profile=instance.user).exists():
        #     return format_html(instance.user.messenger_account.msngr_link)

    get_contacts.allow_tags = True
    get_contacts.short_description = 'Контакты'
