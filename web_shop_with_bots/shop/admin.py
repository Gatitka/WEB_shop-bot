from typing import Any, Union
from django.contrib import admin
from django.http.request import HttpRequest
from django.utils import timezone
from django.utils.html import format_html
from delivery_contacts.utils import get_google_api_key
from tm_bot.models import MessengerAccount
from utils.utils import activ_actions
from .forms import (OrderAddForm, OrderChangeForm,
                    OrderGlovoAdminForm,
                    OrderWoltAdminForm, OrderSmokeAdminForm,
                    OrderNeTaDverAdminForm,
                    OrderChangelistForm, OrderSealTeaAdminForm)
from .models import (Dish, Order, OrderDish, Discount,
                     OrderGlovoProxy, OrderWoltProxy,
                     OrderSmokeProxy, OrderNeTaDverProxy,
                     OrderSealTeaProxy)
from tm_bot.services import (send_message_new_order,
                             send_request_order_status_update)
from django import forms
from .admin_utils import (
    export_orders_to_excel,
    export_full_orders_to_excel,
    get_changelist_extra_context,
    my_get_object,
    my_get_queryset)
from django.core.exceptions import ValidationError
from .utils import get_flag, custom_source, custom_order_number
from rangefilter.filters import (
    DateRangeFilterBuilder, DateRangeQuickSelectListFilter
)
from django.contrib.admin.views.main import ChangeList
from django.urls import reverse, path
from django.shortcuts import redirect
from django.conf import settings
from users.models import user_add_new_order_data
from utils.admin_permissions import has_restaurant_admin_permissions
from delivery_contacts.models import Courier, DeliveryZone, Delivery


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    """Настройки админ панели промо-новостей."""
    list_display = ['id', 'is_active', 'title_rus']
    readonly_fields = ('id', 'created',)
    actions = [*activ_actions]
    search_fields = ('promocode', 'title_rus')
    list_filter = ('is_active',)


class OrderDishInline(admin.TabularInline):
    """Вложенная админка OrderDish для добавления товаров в заказ (создания записей OrderDish)
    сразу в админке заказа (через объект Order)."""
    model = OrderDish
    min_num = 1   # хотя бы 1 блюдо должно быть добавлено
    extra = 0   # чтобы не добавлялись путые поля
    fields = ['dish', 'quantity', 'unit_price', 'unit_amount']
    readonly_fields = ['unit_amount', 'unit_price', 'dish_article', 'order_number']   # 'dish_widget',
    verbose_name = 'товар заказа'
    verbose_name_plural = 'товары заказа'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'dish':
            qs = Dish.objects.all().prefetch_related('translations')
            return forms.ModelChoiceField(queryset=qs)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class CustomChangeList(ChangeList):
    def url_for_result(self, result):
        """
        Return the URL for the "change" view for the given result object.
        """
        app_label = self.opts.app_label

        # Logic to determine the correct proxy model
        if result.source == 'P1-1':
            model_name = 'orderglovoproxy'
        elif result.source == 'P1-2':
            model_name = 'orderwoltproxy'
        elif result.source == 'P2-1':
            model_name = 'ordersmokeproxy'
        elif result.source == 'P2-2':
            model_name = 'ordernetadverproxy'
        elif result.source == 'P3-1':
            model_name = 'ordersealteaproxy'
        else:
            model_name = 'order'

        return reverse(f'admin:{app_label}_{model_name}_change', args=[result.pk])


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Настройки админ панели заказов.
    ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""

    def custom_order_number(self, obj):
        # return custom_order_number(obj)
        return obj.order_number
    custom_order_number.short_description = '№'

    def warning(self, obj):
        # Условие для проверки различных состояний
        help_text = []
        if (obj.delivery.type == 'delivery'
                    and obj.delivery_zone.name == 'уточнить'):
            help_text.append("Уточнить зону доставки.\n")

        if (obj.delivery.type == 'delivery'
                    and obj.courier is None):
            help_text.append("Не назначен курьер.\n")

        if obj.payment_type is None:
            help_text.append("Тип оплаты не определен.\n")

        if obj.process_comment:
            help_text.append("Ошибки в сохранении заказа.\n")

        help_text = "".join(help_text)

        if help_text != '':
            # Возвращение HTML с подсказкой
            return format_html(
                '<span style="color:red;" title="{}">!!!</span>', help_text)
        else:
            return ''
    warning.short_description = '!'

    def info(self, obj):
        source = obj.source
        if source in ['1', '2', '3', '4']:
            # если не через партнеров, а из наших источников заказ
            if obj.delivery.type == 'delivery':
                address = obj.recipient_address

                if address in ['', None]:
                    return '❓нет адреса доставки'

                if obj.delivery_zone.name == 'уточнить':
                    address = format_html('<span style="color:red;">{}</span>',
                                          address)
                return address

            elif obj.delivery.type == 'takeaway':
                return 'самовывоз'
        else:
            return obj.get_source_display()
    info.short_description = 'Адрес'

    def custom_total(self, obj):
        if obj.process_comment:
            return format_html(
                '<span style="color:red;" title="{}">!!!</span>',
                obj.final_amount_with_shipping)
        return obj.final_amount_with_shipping
    custom_total.short_description = format_html('Сумма<br>заказа, DIN')

    def note(self, obj):
        if obj.source in ['3'] + settings.PARTNERS_LIST:
            source = obj.get_source_display()
            source_id = f'{obj.source_id}' if obj.source_id is not None else ''
            if obj.source_id:
                if source == 'TM_Bot':
                    source = f"{source}{obj.orders_bot_id}"
                    return format_html(
                        '{}<br>{}',
                        source, source_id)

                return source_id
            else:
                return '❓нет ID'
        return ''
    note.short_description = 'Примечание'

    def custom_delivery_cost(self, obj):
        #return obj.delivery_cost if obj.delivery_cost != 0 else ''
        if obj.delivery_zone:
            return obj.delivery_zone.delivery_cost
        return ''
    custom_delivery_cost.short_description = format_html('Доставка,<br>DIN')

    def get_contacts(self, instance):
        lang = get_flag(instance)
        name = format_html('{}<br>{}',
                           lang,
                           instance.recipient_name if instance.recipient_name else '')
        msngr_link = ''
        phone = instance.recipient_phone if instance.recipient_phone else ''
        if instance.user:
            name = f'{lang}👤 {instance.recipient_name}'
            if instance.is_first_order:
                name = f'{lang}🥇👤 {instance.recipient_name}'
            if instance.user.messenger_account:
                msngr_link = format_html(instance.user.messenger_account.msngr_link)

        else:
            if instance.msngr_account:
                msngr_link = format_html(instance.msngr_account.msngr_link)

        return format_html('{}<br>{}<br>{}',
                           name,
                           phone,
                           msngr_link)

    get_contacts.allow_tags = True
    get_contacts.short_description = 'Контакты'

    def print_button(self, obj):
        """Adds print button to each row"""
        return format_html(
            '<button type="button" class="print-button" data-id="{}">'
            '🖨️</button>',
            obj.id
        )
    print_button.short_description = 'Печать'
    print_button.allow_tags = True

    list_display = ('custom_order_number', 'warning',
                    'info',
                    'custom_total',
                    'note',
                    'payment_type', 'invoice', 'custom_delivery_cost',
                    'status', 'courier',
                    'get_contacts',
                    'get_delivery_type',
                    'print_button')  # Добавляем кнопку печати в список
    list_editable = ['status', 'invoice', 'courier', 'payment_type']
    # list_display_links = ('custom_order_number',)
    readonly_fields = [
                       'items_qty', 'get_msngr_link',
                       'amount', 'discount_amount',
                       'promocode_disc_amount',
                       # 'auth_fst_ord_disc_amount',
                       # 'takeaway_disc_amount',
                       # 'cash_discount_amount',
                       'discounted_amount',
                       'final_amount_with_shipping',
                       # 'orderdishes_inline',
                       'get_user_data',
                       'get_delivery_type',
                       'get_delivery_cost'
                       ]
    list_filter = (('created', DateRangeQuickSelectListFilter),
                   'status', 'source', 'city', 'courier')
    search_fields = ('recipient_phone', 'msngr_account__msngr_username',
                     'recipient_name')
    inlines = (OrderDishInline,)
    raw_id_fields = ['user', 'msngr_account']
    actions_selection_counter = False   # Controls whether a selection counter is displayed next to the action dropdown. By default, the admin changelist will display it
    actions = [export_orders_to_excel, export_full_orders_to_excel,]
    actions_on_top = True
    list_per_page = 20
    radio_fields = {"payment_type": admin.HORIZONTAL,
                    "delivery": admin.HORIZONTAL,
                    "discount": admin.VERTICAL}

    add_form_template = 'shop/order/add_form.html'
    change_form_template = 'shop/order/change_form.html'
    change_list_template = 'shop/order/change_list.html'

    def get_fieldsets(self, request, obj=None):
        if obj is None:  # Если это форма создания нового заказа
            return [
                ('Данные заказа', {
                    'fields': (
                        ('source', 'source_id', 'invoice'),
                        ('delivery', 'discount', 'payment_type'),
                    )
                }),
                ('Сумма заказа', {
                    'fields': (
                        ('amount', 'final_amount_with_shipping', 'items_qty'),
                    )
                })
            ]

        # Если это форма редактирования существующего заказа, возвращаем полный набор полей
        delivery_classes = ["collapse"]
        if obj and obj.delivery.type == 'delivery':
            delivery_classes = []
        return [
            ('Общие данные заказа', {
                "classes": ["collapse"],
                'fields': (
                    ('process_comment'),
                    ('status', 'language'),
                    ('source', 'source_id'),
                    ('city', 'restaurant'),
                    ('delivery', 'payment_type', 'invoice'),
                )
            }),
            ('Контактная информация', {
                'fields': (
                    ('recipient_name', 'recipient_phone', 'get_msngr_link'),
                    ('user', 'msngr_account', 'get_user_data'),
                    ('delivery_time', 'persons_qty',),
                )
            }),

            ('Доставка', {
                "description": (
                    "После набора блюд в корзину, заполните поле 'адрес' "
                    "и нажмите 'РАССЧИТАТЬ' для определения зоны доставки "
                    "и стоимости."
                ),
                "classes": delivery_classes,
                'fields': (
                    ('recipient_address', 'coordinates', 'address_comment'),
                    ('my_delivery_address', 'my_address_coordinates',
                        'my_address_comments'),
                    ('calculate_delivery_button', 'auto_delivery_zone',
                        'auto_delivery_cost', 'error_message'),
                    ('delivery_zone'),
                    ('delivery_cost'),
                    ('courier'),
                )
            }),
            ('Расчет суммы заказа', {
                'fields': (
                    ('amount', 'get_delivery_cost'),
                    ('discount', 'discount_amount'),
                    ('promocode', 'promocode_disc_amount',),
                    ('manual_discount'),
                    ('discounted_amount'),
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
        ]

    def get_form(self, request, obj=None, **kwargs):
        """
        Выбираем форму в зависимости от действия (создание или редактирование).
        """
        if obj is None:  # Если создается новый заказ
            kwargs['form'] = OrderAddForm
        else:  # Если объект редактируется
            kwargs['form'] = OrderChangeForm

        form = super().get_form(request, obj, **kwargs)
        form.user = request.user  # Передаем текущего пользователя в форму
        return form

    def get_delivery_type(self, obj):
        return obj.delivery.type
    get_delivery_type.short_description = 'Delivery Type'
    get_delivery_type.admin_order_field = 'delivery__type'

    def get_delivery_cost(self, obj):
        return obj.delivery_cost
    get_delivery_cost.short_description = 'Стоимость доставки'
    get_delivery_cost.admin_order_field = 'get_delivery_cost'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # from django.db import connection
        # from django.db.models.query import QuerySet

        # # Получаем все ID заказов напрямую из БД
        # with connection.cursor() as cursor:
        #     cursor.execute("SELECT id FROM shop_order ORDER BY created DESC")
        #     ids = [row[0] for row in cursor.fetchall()]

        # # Создаем QuerySet с этими ID
        # qs = Order.objects.filter(id__in=ids)
        # qs = Order._base_manager.all()
        qs = qs.select_related(
                'user',
                'delivery',
                'delivery_zone',
                'msngr_account',
                'courier',
                'user__messenger_account',
                'restaurant',
                'orders_bot')
        # Проверяем наличие конкретного заказа
        print("Checking order 8887:", qs.filter(id=8887).exists())

        if request.user.is_superuser:
            return qs

        view = request.GET.get('view', None)
        e = request.GET.get('e', None)
        if view == 'all_orders' or e == '1':
            return qs

        restaurant = request.user.restaurant
        if restaurant:
            qs = qs.filter(restaurant=restaurant)
            print("Checking order 8887:", qs.filter(id=8887).exists())
            return qs

        user_id = request.GET.get('user_id')
        if user_id is not None:
            qs = Order.objects.filter(
                    user=user_id).select_related(
                        'user',
                        'delivery',
                        'delivery_zone',
                        'msngr_account',
                        'courier',
                        'user__messenger_account')
        print("Checking order 8887:", qs.filter(id=8887).exists())
        return qs

    def get_object(self, request, object_id, from_field=None):
        model = self.model
        return my_get_object(model, object_id)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/change/', self.change_view, name='order_change'),
        ]
        return custom_urls + urls

    def get_changelist(self, request, **kwargs):
        return CustomChangeList

    def changelist_view(self, request, extra_context=None):
        # Сначала получаем существующий контекст
        extra_context = get_changelist_extra_context(request, extra_context)
        return super(OrderAdmin, self).changelist_view(
            request, extra_context=extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        # Добавление ключа API Google Maps в контекст
        extra_context["GOOGLE_API_KEY"] = get_google_api_key()

        return super().add_view(
            request,
            form_url,
            extra_context=extra_context
        )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        order = Order.objects.get(pk=object_id)
        # return redirect(order.get_admin_url())

        admin_url = order.get_admin_url()
        if admin_url != request.path:  # Проверяем, не совпадает ли текущий URL с URL, который мы пытаемся обработать
            return redirect(admin_url)
        return super().change_view(request, object_id, form_url, extra_context)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)

        if obj and obj.origin in ['1', '4']:
            self.form.base_fields['recipient_name'].required = True
            self.form.base_fields['recipient_phone'].required = True
        self.form.base_fields['delivery'].required = True

        return fields

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)

        if db_field.name == 'delivery':
            formfield.required = True

        elif (db_field.name == 'auto_delivery_zone'
                or db_field.name == 'auto_delivery_cost'):

            kwargs['widget'] = admin.widgets.AdminTextInputWidget(
                attrs={'readonly': 'readonly'})

        return formfield

    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     """
    #     Обрабатываем поле ForeignKey для курьера и фильтруем по городу заказа
    #     только при редактировании объекта.
    #     """
    #     if db_field.name == "courier":
    #         # Проверяем URL. Если это changelist, не делаем фильтрацию
    #         if request.resolver_match.url_name == 'shop_order_changelist':  # Замените на правильное имя URL
    #             # Если это changelist, показываем всех курьеров
    #             kwargs["queryset"] = Courier.objects.all()
    #         else:
    #             # Если это редактирование объекта, фильтруем курьеров по городу заказа
    #             obj_id = request.resolver_match.kwargs.get('object_id')
    #             if obj_id:
    #                 # Извлекаем только необходимый объект заказа (один запрос)
    #                 order = Order.objects.only('city').get(pk=obj_id)
    #                 # Фильтруем курьеров по городу заказа
    #                 kwargs["queryset"] = Courier.objects.filter(city=order.city)
    #             else:
    #                 # Если создаётся новый заказ, можно вернуть пустой список курьеров
    #                 kwargs["queryset"] = Courier.objects.all()

    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)


    def save_related(self, request, form, formsets, change):
        """
        Given the ``HttpRequest``, the parent ``ModelForm`` instance, the
        list of inline formsets and a boolean value based on whether the
        parent is being added or changed, save the related objects to the
        database. Note that at this point save_form() and save_model() have
        already been called.
        """
        form.save_m2m()
        for formset in formsets:
            self.save_formset(request, form, formset, change=change)
        if not change:
            if form.instance.source not in settings.PARTNERS_LIST:
                send_message_new_order(form.instance)
            if form.instance.user:
                user_add_new_order_data(form.instance)

        if form.instance.source == '3':
            if settings.SEND_BOTOBOT_UPDATES:
                new_status = form.cleaned_data.get('status')
                old_status = form.initial.get('status')

                if old_status is not None and new_status != old_status:
                    send_request_order_status_update(
                        new_status, int(form.instance.source_id),
                        form.instance.orders_bot)

    def get_changelist_form(self, request, **kwargs):
        """
        Используем кастомную форму в changelist для динамической фильтрации курьеров,
        с учётом того, является ли пользователь суперпользователем.
        """
        # Передаем request в форму, чтобы учитывать информацию о пользователе
        kwargs['form'] = OrderChangelistForm
        form = super().get_changelist_form(request, **kwargs)

        # Нужно передать request в форму вручную
        class CustomOrderChangelistForm(form):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request  # Добавляем request в параметры формы
                return form(*args, **kwargs)

        return CustomOrderChangelistForm

    def get_actions(self, request):
        actions = super().get_actions(request)

        # Проверяем параметр 'view' в запросе
        if (request.GET.get('view') == 'all_orders'
                or request.GET.get('e') == '1'):
            # Если пользователь не суперпользователь, убираем все actions
            if not request.user.is_superuser:
                return {}

        # Возвращаем исходные actions, если условие не выполнено
        return actions

        # после сохранения НОВОГО заказа и его связей
        # отправляется сообщение о новом заказе

    # def orderdishes_inline(self, *args, **kwargs):
    #     context = getattr(self.response, 'context_data', None) or {}
    #     inline = context['inline_admin_formset'] = context['inline_admin_formsets'].pop(0)
    #     return get_template(inline.opts.template).render(context, self.request)

    # def render_change_form(self, request, context=None, *args, **kwargs):
    #     # self.request = request
    #     # self.response = super().render_change_form(request, *args, **kwargs)
    #     # return self.response
    #     if context:
    #         instance = context['adminform'].form.instance  # get the model instance from modelform
    #         instance.request = request
    #         instance.response = super().render_change_form(request, context, *args, **kwargs)
    #         return instance.response

    # ------ ОТОБРАЖЕНИЕ ССЫЛКИ НА ЧАТ С КЛИЕНТОМ -----

    def get_msngr_link(self, instance):
        try:
            return format_html(instance.user.messenger_account.msngr_link)
        except:
            try:
                return format_html(instance.msngr_account.msngr_link)
            except:
                return '-'

    get_msngr_link.allow_tags = True
    get_msngr_link.short_description = 'Чат'

    def get_user_data(self, instance):
        if instance.user and instance.msngr_account is None:
            return instance.user.get_orders_data()
        elif instance.msngr_account and instance.user is None:
            return instance.msngr_account.get_orders_data()
        # elif instance.msngr_account and instance.user:
        # вернуть данные из зареганого пользователя, т.к. по умолчанию все заказы
        # уже объединились в его аккаунте
        else:
            return ''
    get_user_data.allow_tags = True
    get_user_data.short_description = 'Инфо'

    # ------ ПЕРМИШЕНЫ -----

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return super().has_change_permission(request)

        return has_restaurant_admin_permissions(
            'delivery_contacts.change_orders_rest',
            request, obj)


class OrderDishPartnerInline(admin.TabularInline):
    model = OrderDish
    min_num = 1
    extra = 0
    fields = ['dish', 'quantity', 'unit_price', 'unit_amount']
    readonly_fields = ['unit_amount', 'unit_price', 'dish_article', 'order_number']
    verbose_name = 'товар заказа'
    verbose_name_plural = 'товары заказа'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'dish':
            qs = Dish.objects.all().prefetch_related('translations')
            return forms.ModelChoiceField(queryset=qs)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class BaseOrderProxyAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'status', 'custom_total', 'note')
    list_editable = ['status']
    list_display_links = ('order_number',)
    readonly_fields = ['items_qty', 'amount', 'created', 'order_number', 'final_amount_with_shipping']
    list_filter = (('created', DateRangeQuickSelectListFilter), 'status')
    search_fields = ('order_number', 'source_id')
    inlines = (OrderDishPartnerInline,)
    actions_selection_counter = False
    actions_on_top = True
    actions = [export_orders_to_excel, export_full_orders_to_excel]
    list_per_page = 10
    change_list_template = 'shop/order/change_list_partner.html'
    source_code = None  # должен быть переопределен в дочерних классах

    class Media:
        js = (
            'my_admin/js/shop/calculate_add_order_fields.js',
        )

    # def custom_order_number(self, obj):
    #     return f"{obj.order_number}/{obj.id}"
    # custom_order_number.short_description = '№'

    # def custom_created(self, obj):
    #     local_time = obj.created.astimezone(timezone.get_current_timezone())
    #     formatted_time = local_time.strftime(
    #         '<span style="color:green;font-weight:bold;">%H:%M</span><br>%d.%m'
    #         if obj.status == 'WCO' else '%H:%M<br>%d.%m'
    #     )
    #     return format_html(formatted_time)
    # custom_created.short_description = 'создан'

    def custom_total(self, obj):
        return obj.final_amount_with_shipping
    custom_total.short_description = format_html('Сумма<br>заказа, DIN')

    def note(self, obj):
        if obj.source in settings.PARTNERS_LIST:
            if obj.source_id:
                source_id = f'{obj.source_id}' if obj.source_id is not None else ''
                return source_id
            else:
                return '❓нет ID'
    note.short_description = 'Примечание'

    def get_queryset(self, request):
        if not self.source_code:
            raise NotImplementedError("source_code must be set in child class")
        qs = super().get_queryset(request).filter(
           source=self.source_code
       ).select_related('restaurant')
        return my_get_queryset(request, qs)

    def get_object(self, request, object_id, from_field=None):
        if not self.source_code:
            raise NotImplementedError("source_code must be set in child class")
        return my_get_object(self.model, object_id, source=self.source_code)

    def changelist_view(self, request, extra_context=None):
        extra_context = get_changelist_extra_context(
            request,
            extra_context,
            source=self.source_code
        )
        return super().changelist_view(request, extra_context=extra_context)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return super().has_change_permission(request)
        return has_restaurant_admin_permissions(
            'delivery_contacts.change_orders_rest',
            request, obj
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.user = request.user
        return form

    def get_changeform_initial_data(self, request):
        return {'source': self.source_code}

    def get_fieldsets(self, request, obj=None):
        if obj is None:  # Если это форма создания нового заказа
            return [
                ('Данные заказа', {
                    'fields': (
                        ('source_id', 'source'),
                        ('final_amount_with_shipping', 'items_qty')
                    )
                }),
            ]
        # Если это форма редактирования существующего заказа, возвращаем полный набор полей
        return [
            ('Данные заказа', {
                    'fields': (
                        ('status'),
                        ('source_id', 'source'),
                        ('final_amount_with_shipping', 'items_qty')
                    )
                }),
        ]



@admin.register(OrderGlovoProxy)
class OrderGlovoProxyAdmin(BaseOrderProxyAdmin):
    form = OrderGlovoAdminForm
    source_code = 'P1-1'

@admin.register(OrderWoltProxy)
class OrderWoltProxyAdmin(BaseOrderProxyAdmin):
    form = OrderWoltAdminForm
    source_code = 'P1-2'

@admin.register(OrderSmokeProxy)
class OrderSmokeProxyAdmin(BaseOrderProxyAdmin):
    form = OrderSmokeAdminForm
    source_code = 'P2-1'

@admin.register(OrderNeTaDverProxy)
class OrderNeTaDverProxyAdmin(BaseOrderProxyAdmin):
    form = OrderNeTaDverAdminForm
    source_code = 'P2-2'

@admin.register(OrderSealTeaProxy)
class OrderSealTeaProxyAdmin(BaseOrderProxyAdmin):
    form = OrderSealTeaAdminForm
    source_code = 'P3-1'

# @admin.register(OrderGlovoProxy)
# class OrderGlovoProxyAdmin(admin.ModelAdmin):

#     def custom_order_number(self, obj):
#         # краткое название поля в list
#         return f"{obj.order_number}/{obj.id}"
#     custom_order_number.short_description = '№'

#     def custom_created(self, obj):
#         # Преобразование поля datetime в строку с помощью strftime()

#         local_time = obj.created.astimezone(timezone.get_current_timezone())
#         if obj.status == 'WCO':
#             formatted_time = local_time.strftime('<span style="color:green;font-weight:bold;">%H:%M</span><br>%d.%m')
#         else:
#             formatted_time = local_time.strftime('%H:%M<br>%d.%m')
#         return format_html(formatted_time)
#     custom_created.short_description = 'создан'

#     list_display = ('custom_order_number', 'custom_created',
#                     'status', 'custom_total')
#     list_editable = ['status',]
#     list_display_links = ('custom_order_number', )
#     readonly_fields = ['items_qty', 'amount', 'created', 'order_number',
#                        'final_amount_with_shipping']
#     list_filter = (('created', DateRangeFilterBuilder()), 'status')
#     search_fields = ('order_number',)
#     inlines = (OrderDishGlovoWoltInline,)
#     actions_selection_counter = False   # Controls whether a selection counter is displayed next to the action dropdown. By default, the admin changelist will display it
#     actions_on_top = True
#     actions = [export_orders_to_excel, export_full_orders_to_excel,]
#     list_per_page = 10
#     fieldsets = (
#         ('Данные заказа', {
#             "fields": (
#                 ('status', 'source_id'),
#                 ('final_amount_with_shipping', 'items_qty'),

#             ),
#         }),
#         # ('Город/ресторан', {
#         #     "classes": ["collapse"],
#         #     'fields': (
#         #         ('city', 'restaurant'),
#         #     )
#         # }),
#     )
#     form = OrderGlovoAdminForm
#     change_list_template = 'order/change_list_partner.html'

#     def custom_total(self, obj):
#         # краткое название поля в list
#         return obj.final_amount_with_shipping
#     custom_total.short_description = format_html('Сумма<br>заказа, DIN')

#     def get_queryset(self, request):
#         qs = super().get_queryset(request).filter(
#                 source='P1-1'
#             ).select_related('restaurant')
#         return my_get_queryset(request, qs)

#     def get_object(self, request, object_id, from_field=None):
#         model = self.model
#         return my_get_object(model, object_id, source='P1-1')

#     def changelist_view(self, request, extra_context=None):
#         extra_context = get_changelist_extra_context(request,
#                                                      extra_context,
#                                                      source='P1-1')

#         return super(OrderGlovoProxyAdmin, self).changelist_view(
#             request, extra_context=extra_context)

#     def has_change_permission(self, request, obj=None):
#         if request.user.is_superuser:
#             return super().has_change_permission(request)

#         return has_restaurant_admin_permissions(
#             'delivery_contacts.change_orders_rest',
#             request, obj)

#     def get_form(self, request, obj=None, **kwargs):
#         """
#         Переопределяем метод get_form для передачи пользователя в форму.
#         """
#         form = super().get_form(request, obj, **kwargs)
#         form.user = request.user  # Передаем текущего пользователя в форму
#         return form


# @admin.register(OrderWoltProxy)
# class OrderWoltProxyAdmin(admin.ModelAdmin):

#     def custom_order_number(self, obj):
#         # краткое название поля в list
#         return f"{obj.order_number}/{obj.id}"
#     custom_order_number.short_description = '№'

#     def custom_created(self, obj):
#         # Преобразование поля datetime в строку с помощью strftime()

#         local_time = obj.created.astimezone(timezone.get_current_timezone())
#         if obj.status == 'WCO':
#             formatted_time = local_time.strftime('<span style="color:green;font-weight:bold;">%H:%M</span><br>%d.%m')
#         else:
#             formatted_time = local_time.strftime('%H:%M<br>%d.%m')
#         return format_html(formatted_time)
#     custom_created.short_description = 'создан'

#     list_display = ('custom_order_number', 'custom_created',
#                     'status', 'custom_total')
#     list_editable = ['status',]
#     list_display_links = ('custom_order_number', )
#     readonly_fields = ['items_qty', 'amount', 'created', 'order_number',
#                        'final_amount_with_shipping']
#     list_filter = (('created', DateRangeFilterBuilder()), 'status')
#     search_fields = ('order_number',)
#     inlines = (OrderDishGlovoWoltInline,)
#     actions_selection_counter = False   # Controls whether a selection counter is displayed next to the action dropdown. By default, the admin changelist will display it
#     actions_on_top = True
#     actions = [export_orders_to_excel, export_full_orders_to_excel,]
#     list_per_page = 10
#     fieldsets = (
#         ('Данные заказа', {
#             "fields": (
#                 ('status', 'source_id'),
#                 ('final_amount_with_shipping', 'items_qty'),
#             ),
#         }),
#         # ('Город/ресторан', {
#         #     "classes": ["collapse"],
#         #     'fields': (
#         #         ('city', 'restaurant'),
#         #     )
#         # }),
#     )
#     form = OrderWoltAdminForm
#     change_list_template = 'order/change_list_partner.html'

#     def custom_total(self, obj):
#         # краткое название поля в list
#         return obj.final_amount_with_shipping
#     custom_total.short_description = format_html('Сумма<br>заказа, DIN')

#     def get_queryset(self, request):
#         qs = super().get_queryset(request).filter(
#                 source='P1-2'
#             ).select_related('restaurant')
#         return my_get_queryset(request, qs)

#     def get_object(self, request, object_id, from_field=None):
#         model = self.model
#         return my_get_object(model, object_id, source='P1-2')

#     def changelist_view(self, request, extra_context=None):
#         extra_context = get_changelist_extra_context(request,
#                                                      extra_context,
#                                                      source='P1-2')

#         return super(OrderWoltProxyAdmin, self).changelist_view(
#             request, extra_context=extra_context)

#     def has_change_permission(self, request, obj=None):
#         if request.user.is_superuser:
#             return super().has_change_permission(request)

#         return has_restaurant_admin_permissions(
#             'delivery_contacts.change_orders_rest',
#             request, obj)

#     def get_form(self, request, obj=None, **kwargs):
#         """
#         Переопределяем метод get_form для передачи пользователя в форму.
#         """
#         form = super().get_form(request, obj, **kwargs)
#         form.user = request.user  # Передаем текущего пользователя в форму
#         return form


# @admin.register(OrderSmokeProxy)
# class OrderSmokeProxyAdmin(admin.ModelAdmin):

#     def custom_order_number(self, obj):
#         # краткое название поля в list
#         return f"{obj.order_number}/{obj.id}"
#     custom_order_number.short_description = '№'

#     def custom_created(self, obj):
#         # Преобразование поля datetime в строку с помощью strftime()

#         local_time = obj.created.astimezone(timezone.get_current_timezone())
#         if obj.status == 'WCO':
#             formatted_time = local_time.strftime(
#                 '<span style="color:green;font-weight:bold;">%H:%M</span><br>%d.%m')
#         else:
#             formatted_time = local_time.strftime('%H:%M<br>%d.%m')
#         return format_html(formatted_time)
#     custom_created.short_description = 'создан'

#     list_display = ('custom_order_number', 'custom_created',
#                     'status', 'custom_total')
#     list_editable = ['status',]
#     list_display_links = ('custom_order_number', )
#     readonly_fields = ['items_qty', 'amount', 'created', 'order_number',
#                        'final_amount_with_shipping']
#     list_filter = (('created', DateRangeFilterBuilder()), 'status')
#     search_fields = ('order_number',)
#     inlines = (OrderDishGlovoWoltInline,)
#     actions_selection_counter = False   # Controls whether a selection counter is displayed next to the action dropdown. By default, the admin changelist will display it
#     actions_on_top = True
#     actions = [export_orders_to_excel, export_full_orders_to_excel,]
#     list_per_page = 10
#     fieldsets = (
#         ('Данные заказа', {
#             "fields": (
#                 ('status', 'source_id'),
#                 ('final_amount_with_shipping', 'items_qty'),
#             ),
#         }),
#         # ('Город/ресторан', {
#         #     "classes": ["collapse"],
#         #     'fields': (
#         #         ('city', 'restaurant'),
#         #     )
#         # }),
#     )
#     form = OrderSmokeAdminForm
#     change_list_template = 'order/change_list_partner.html'

#     def custom_total(self, obj):
#         # краткое название поля в list
#         return obj.final_amount_with_shipping
#     custom_total.short_description = format_html('Сумма<br>заказа, DIN')

#     def get_queryset(self, request):
#         qs = super().get_queryset(request).filter(
#                 source='P2-1'
#             ).select_related('restaurant')
#         return my_get_queryset(request, qs)

#     def get_object(self, request, object_id, from_field=None):
#         model = self.model
#         return my_get_object(model, object_id, source='P2-1')

#     def changelist_view(self, request, extra_context=None):
#         extra_context = get_changelist_extra_context(request,
#                                                      extra_context,
#                                                      source='P2-1')
#         return super(OrderSmokeProxyAdmin, self).changelist_view(
#             request, extra_context=extra_context)

#     def has_change_permission(self, request, obj=None):
#         if request.user.is_superuser:
#             return super().has_change_permission(request)

#         return has_restaurant_admin_permissions(
#             'delivery_contacts.change_orders_rest',
#             request, obj)

#     def get_form(self, request, obj=None, **kwargs):
#         """
#         Переопределяем метод get_form для передачи пользователя в форму.
#         """
#         form = super().get_form(request, obj, **kwargs)
#         form.user = request.user  # Передаем текущего пользователя в форму
#         return form

################################################################ КОРЗИНА
# class CartDishInline(admin.TabularInline):
#     """
#     Вложенная админка CartDish для добавления товаров в заказ
#     (создания записей CartDish) сразу в админке заказа (через объект Cart).
#     """
#     model = CartDish
#     min_num = 1   # хотя бы 1 блюдо должно быть добавлено
#     extra = 0   # чтобы не добавлялись путые поля
#     readonly_fields = ['amount', 'unit_price', 'dish_article', 'cart_number',]
#     autocomplete_fields = ['dish']

#     verbose_name = 'товар корзины'
#     verbose_name_plural = 'товары корзины'

#     # class Media:
#     #     js = ('js/shop/admin/cartitem_data_admin_request.js',)

#     def get_queryset(self, request):
#         return super().get_queryset(request).prefetch_related('dish__translations', 'cart__user__messenger_account')

# @admin.register(ShoppingCart)
# class ShoppingCartAdmin(admin.ModelAdmin):
#     """Настройки админ панели карзины.
#     ДОДЕЛАТЬ: отображение отображение итоговых сумм при редакции заказа"""
#     list_display = ('pk', 'complited', 'user',
#                     'created', 'discounted_amount')
#     readonly_fields = ['created', 'discounted_amount',
#                        'device_id', 'amount', 'discount', 'items_qty']
#     list_filter = ('created', 'complited')
#     raw_id_fields = ['user', ]
#     inlines = (CartDishInline,)
#     fields = (('created', 'complited'),
#               ('user', 'device_id'),
#               ('items_qty', 'amount'),
#               ('promocode', 'discount'),
#               ('discounted_amount'),
#               )
#     # change_form_template = 'admin/shop/shoppingcart/my_shoping_cart_change_form.html'

#     # class Media:
#     #     js = ('my_admin/js/shop/cartitem_data_admin_request.js',)

#     def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
#         return super().get_queryset(request).prefetch_related('user')
