import json
from django.conf import settings
from django import forms

from delivery_contacts.models import Delivery, Courier, Restaurant
from delivery_contacts.services import get_delivery_zone
from delivery_contacts.utils import parce_coordinates
from shop.models import (Order, OrderGlovoProxy, OrderWoltProxy,
                         OrderSmokeProxy, OrderNeTaDverProxy, OrderSealTeaProxy,
                         DeliveryZone, Delivery, Discount)
from shop.validators import (validate_delivery_time)
from phonenumber_field.validators import validate_international_phonenumber
from users.models import UserAddress
from users.validators import validate_first_and_last_name
from tm_bot.services import get_bot_id_by_city
import re
from django.forms.widgets import Select
from django.db.models import Q
import logging


#logger = logging.getLogger(__name__)


def url_params_from_lookup_dict(lookups):
    """
    Convert the type of lookups specified in a ForeignKey limit_choices_to
    attribute to a dictionary of query parameters
    """
    params = {}
    if lookups and hasattr(lookups, 'items'):
        for k, v in lookups.items():
            if callable(v):
                v = v()
            if isinstance(v, (tuple, list)):
                v = ','.join(str(x) for x in v)
            elif isinstance(v, bool):
                v = ('0', '1')[v]
            else:
                v = str(v)
            params[k] = v
    return params


class FilteredByUserAndCityWidget(Select):
    """
    Кастомный виджет для фильтрации объектов по городу и уровню доступа пользователя.
    """
    def __init__(self, city, is_superuser, model_class, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.city = city
        self.is_superuser = is_superuser
        self.model_class = model_class

    def get_context(self, name, value, attrs):
        self.choices = [(None, '--------')] if self.model_class == Courier else []

        if self.is_superuser:
            queryset = self.model_class.objects.all()
        else:
            queryset = self.model_class.objects.filter(city=self.city)

        self.choices += [(obj.id, str(obj) if self.model_class in [Courier, Delivery] else obj.name)
                         for obj in queryset]
        return super().get_context(name, value, attrs)


def get_filtered_delivery_zones(user):
    # Базовый запрос для всех пользователей
    base_query = Q(name__in=['уточнить', 'по запросу'])

    if user.is_superuser:
        return DeliveryZone.objects.all()
    else:
        # Получаем города, к которым у пользователя есть доступ
        user_cities = user.restaurant.city
        user_query = base_query | Q(city=user_cities)
        return DeliveryZone.objects.filter(user_query).distinct()


class OrderAddForm(forms.ModelForm):
    invoice = forms.ChoiceField(
        choices=((True, 'Да'), (False, 'Нет')),
        widget=forms.RadioSelect,
        label='Чек',
        initial=True  # Устанавливаем дефолтное значение как 'Да'
    )

    # delivery = forms.ChoiceField(
    #     choices=((True, 'Да'), (False, 'Нет')),
    #     widget=forms.RadioSelect,
    #     label='Доставка',
    #     initial=False  # Устанавливаем дефолтное значение как 'Да'
    # )

    order_type = forms.ChoiceField(
        choices=settings.ORDER_TYPES,
        label='Тип заказа',
        initial='T'  # Default to Delivery
    )

    bot_order = forms.ChoiceField(
        choices=((False, 'Нет'), (True, 'Да')),
        widget=forms.RadioSelect,
        label='Заказ из бота',
        initial=False,
        required=False
    )

    # error_message = forms.CharField(
    #     label='ошибка',
    #     widget=forms.TextInput(
    #         attrs={
    #             'style':
    #             'font-size: small; color: red; display: none; width: 900px;'}),
    #     required=False
    # )

    class Meta:
        model = Order
        fields = ['source', 'source_id', 'amount', 'final_amount_with_shipping',
                  'delivery', 'invoice', 'items_qty', 'discount', 'payment_type',
                  'recipient_name', 'recipient_phone', 'recipient_address',
                  'address_comment', 'delivery_time', 'delivery_zone', 'delivery_cost',
                  'manual_discount', 'comment', 'coordinates', 'city']  # Только необходимые поля
        widgets = {
            'city': forms.HiddenInput(),  # Использовать скрытое поле
            'coordinates': forms.HiddenInput(),  # Использовать скрытое поле
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs),
        user = self.user

        # Устанавливаем значение по умолчанию для города и ресторана
        # if self.instance.pk is None and not user.is_superuser:
        #     set_admin_data(self, user)
        if self.instance.pk is None and user and not user.is_superuser and hasattr(user, 'city') and user.city:
            self.fields['city'].initial = user.city
            self.initial['city'] = user.city  # Также устанавливаем в initial

        # Исключаем скидки на 1й заказ (1) и на оплату наличными при доставке (3)
        if 'discount' in self.fields:
            filtered_discounts = [(None, '---------')] + [
                (discount.id, str(discount))
                for discount in Discount.objects.all()
                if discount.id not in [1, 3]
            ]
            self.fields['discount'].choices = filtered_discounts

        if not user.is_superuser:
            self.fields['delivery_zone'].queryset = get_filtered_delivery_zones(user)

        self.fields['manual_discount'].required = False

    def clean_order_type(self):
        """Process the order_type field to determine delivery type and order_type"""
        order_type = self.cleaned_data.get('order_type')
        city = self.cleaned_data.get('city') or (self.user.city if hasattr(self.user, 'city') else None)
        bot_order = self.data.get('bot_order')
        # Set source based on order_type
        if order_type in ['D', 'T']:  # For Delivery or Takeaway
            if bot_order == 'True' or bot_order is True:
                self.cleaned_data['source'] = '3'  # Bot order
                self.instance.source = '3'
            else:
                self.cleaned_data['source'] = '1'  # Internal order
                self.instance.source = '1'

            # Set delivery type based on order_type
            if order_type == 'D':  # Delivery
                delivery = Delivery.objects.get(city=city, type='delivery')
            else:  # Takeaway
                delivery = Delivery.objects.get(city=city, type='takeaway')

            self.instance.delivery = delivery
            self.cleaned_data['delivery'] = delivery

        else:
            # For partner orders, set source to match order_type
            self.cleaned_data['source'] = order_type
            self.instance.source = order_type

            delivery = Delivery.objects.get(city=city, type='takeaway')
            self.instance.delivery = delivery
            self.cleaned_data['delivery'] = delivery

        return order_type

    def clean_source_id(self):
        '''Поле source_id обязательно для заказов,
        оформленных через партнеров и бота'''
        order_type = self.data.get('order_type')
        source_id = self.data.get('source_id')
        if order_type in (settings.PARTNERS_LIST + ['3']):
            if source_id in ['', None]:
                raise forms.ValidationError(
                    "Внесите номер заказа в источнике.")

        return source_id

    # def clean_payment_type(self):
    #     '''Поле payment_type обязательно для заказов,
    #     оформленных НЕ через партнеров.'''
    #     order_type = self.data.get('order_type')
    #     # if source in settings.PARTNERS_LIST:
    #     #     if source == 'P2-2':
    #     #         return 'cash'
    #     #     else:
    #     #         return None
    #     payment_type = self.data.get('payment_type')
    #     if order_type not in settings.PARTNERS_LIST:
    #         if payment_type in ['', None]:
    #             raise forms.ValidationError(
    #                 "Выберите способ оплаты.")

    #     return payment_type

    # def clean_recipient_address(self):
    #     order_type = self.cleaned_data.get('order_type')
    #     recipient_address = self.cleaned_data.get('recipient_address')

    #     # if order_type is not None and order_type == 'D':
    #         ## coordinates = self.data.get('coordinates')
    #         # if recipient_address is None or recipient_address == '':
    #         #     raise forms.ValidationError(
    #         #         "Проверьте указан ли адрес доставки клиенту.")
    #         #     # Проверяем, содержит ли адрес только буквы, цифры и пробелы
    #         # if not re.search(r'\d+', recipient_address):
    #         #     raise forms.ValidationError("Укажите номер дома.")

    #     return recipient_address

    def clean_delivery_zone(self):
        order_type = self.cleaned_data.get('order_type')
        delivery_zone = self.cleaned_data.get('delivery_zone')
        if order_type is not None and order_type == 'D':
            if delivery_zone is None:
                return DeliveryZone.objects.get(name='уточнить')
            # coordinates = self.cleaned_data.get('coordinates')
            # lat, lon = parce_coordinates(coordinates)
            # if delivery_zone is None:
            #     try:
            #         delivery_zone = get_delivery_zone(
            #             self.cleaned_data.get('city', 'Beograd'),
            #             lat, lon)
            #         if delivery_zone.name == 'уточнить':
            #             raise forms.ValidationError(
            #                 ("Введенный адрес находится вне зоны "
            #                     "обслуживания. Проверьте адрес или внесите "
            #                     "вручную зону и цену доставки.")
            #             )
            #         return delivery_zone

            #     except AttributeError:
            #         raise forms.ValidationError(
            #                 ("Для введенного адреса невозможно получить "
            #                  "координаты и расчитать зону доставки. "
            #                  "Проверьте адрес или внесите "
            #                  "вручную зону и цену доставки.")
            #             )

            # else:
            #     if delivery_zone.name == 'по запросу':
            #         return delivery_zone

        return delivery_zone

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('city') and hasattr(self.user, 'city') and self.user.city:
            cleaned_data['city'] = self.user.city
            self.instance.city = self.user.city

        cleaned_data['restaurant'] = self.user.restaurant
        cleaned_data['created_by'] = 2
        cleaned_data['status'] = 'CFD'
        self.instance.restaurant = self.user.restaurant
        self.instance.created_by = 2
        self.instance.status = 'CFD'

        if cleaned_data['source'] == '3':
            cleaned_data['orders_bot'] = get_bot_id_by_city(self.user.city)[1]
            self.instance.orders_bot = get_bot_id_by_city(self.user.city)[0]

        delivery = cleaned_data['delivery']
        if delivery.type == 'takeaway':
            # При отключении доставки сохраняем данные полей, но не используем их при сохранении
            # Они будут очищены при сохранении формы
            self._saved_delivery_zone = self.cleaned_data.get('delivery_zone')
            self._saved_delivery_cost = self.cleaned_data.get('delivery_cost')
            self._saved_recipient_address = self.cleaned_data.get('recipient_address')
            self._saved_coordinates = self.cleaned_data.get('coordinates')
            self._saved_address_comment = self.cleaned_data.get('address_comment')

            # Очищаем поля доставки
            self.cleaned_data['delivery_zone'] = None
            self.cleaned_data['delivery_cost'] = 0
            self.cleaned_data['recipient_address'] = None
            self.cleaned_data['coordinates'] = None
            self.cleaned_data['address_comment'] = None

            self.instance.delivery_zone = None
            self.instance.delivery_cost = 0
            self.instance.recipient_address = None
            self.instance.coordinates = None
            self.instance.address_comment = None

            if cleaned_data['source'] in settings.PARTNERS_LIST:
                # Очищаем поля скидок
                self.cleaned_data['manual_discount'] = 0
                self.instance.manual_discount = 0

                # Очищаем поля контактов
                self.cleaned_data['recipient_name'] = None
                self.cleaned_data['recipient_phone'] = None

                self.instance.recipient_name = None
                self.instance.recipient_phone = None

        return cleaned_data

    def save(self, commit=True):
        """
        Включаем режим редактирования админом перед сохранением
        admin.save_model() вызывает один раз сейф, но при создании он вызывается 2жды
        и нужно еще раз передать is_admin_mode=True в сохранение
        """
        instance = super().save(commit=False)  # Всегда получаем несохраненный экземпляр

        if self.cleaned_data.get('created_by') is None:
            instance.created_by = 2

        # Всегда сохраняем с флагом is_admin_mode=True
        instance.save(is_admin_mode=True)

        if commit and hasattr(self, 'save_m2m'):
            self.save_m2m()

        return instance


class OrderChangeForm(forms.ModelForm):

    process_comment = forms.CharField(
                label='Ошибки при сохранении',
                required=False,
                widget=forms.Textarea(attrs={
                                            'autocomplete': 'on',
                                            'class': 'vLargeTextField',
                                            'maxlength': 500,
                                        }),
                help_text=(
                    "После исправления ошибок сохранения заказа "
                    "удалите комент."
                ))

    recipient_address = forms.CharField(
               label='Адрес доставки',
               required=False,
               widget=forms.TextInput(attrs={'size': '40',
                                             'autocomplete': 'on',
                                             'class': 'basicAutoComplete',
                                             'style': 'width: 900px;'}))

    my_delivery_address = forms.ChoiceField(
        label='Мои адреса',
        required=False,
        choices=[]
    )

    my_address_comments = forms.CharField(widget=forms.HiddenInput(),
                                          required=False)
    my_address_coordinates = forms.CharField(widget=forms.HiddenInput(),
                                             required=False)
    auto_delivery_zone = forms.CharField(label='Зона доставки (автом)',
                                         required=False)
    auto_delivery_cost = forms.DecimalField(label='Стоимость доставки (автом)',
                                            required=False,
                                            decimal_places=2)
    calculate_delivery_button = forms.CharField(
        label='Рассчитать стоимость доставки.',
        widget=forms.TextInput(
                        attrs={'type': 'button',
                               'value': 'Рассчитать',
                               'data-error': 'calculate-delivery-error'}),
        required=False,
        # help_text=(
        #     "Если zone определяется (прим. zone3), то поля   "
        #     "'ЗОНА ДОСТАВКИ, СТОИМОСТЬ ДОСТАВКИ'   можно не заполнять.<br><br>"
        #     "Если результат = 'УТОЧНИТЬ', то нужно:<br>"
        #     " - уточнить адрес;<br>"
        #     " - выбрать вручную одну из zone;<br>"
        #     " - выбрать зону 'ПО ЗАПРОСУ' и вручную внести стоимость доставки.<br><br>"
        #     "Для сохранения нестандартной стоимости в стандартной зоне, "
        #     "смените зону на 'ПО ЗАПРОСУ' и внесите свою стоимость."
        #     )
    )
    error_message = forms.CharField(
        label='ошибка',
        widget=forms.TextInput(
            attrs={
                'style':
                'font-size: small; color: red; display: none; width: 900px;'}),
        required=False
    )
    calc_message = forms.CharField(
        label='комм.',
        widget=forms.TextInput(
            attrs={
                'style':
                'font-size: small; color: red; display: none; width: 900px;'}),
        required=False
    )
    invoice = forms.ChoiceField(
        choices=((True, 'Да'), (False, 'Нет')),
        widget=forms.RadioSelect,
        label='чек',
        initial=True  # Устанавливаем дефолтное значение как 'Да'
    )

    # flat = forms.CharField(
    #            label='Квартира',
    #            max_length=20,
    #            required=False,
    #            widget=forms.TextInput(attrs={'size': '2',
    #                                          'autocomplete': 'on'}))

    # floor = forms.CharField(
    #            label='Этаж',
    #            max_length=20,
    #            required=False,
    #            widget=forms.TextInput(attrs={'size': '2',
    #                                          'autocomplete': 'on'}))

    # interfon = forms.CharField(
    #            label='Домофон',
    #            max_length=20,
    #            required=False,
    #            widget=forms.TextInput(attrs={'size': '5',
    #                                          'autocomplete': 'on'}))
    # user = forms.CharField(
    #     required=False,
    #     widget=ForeignKeyRawIdWidget(
    #         Order._meta.get_field('user').remote_field,
    #         admin.site)
    # )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.user

        model_fields = {f.name: f for f in Order._meta.fields}
        for field_name, field in model_fields.items():
            if field_name not in self.fields:
                formfield = field.formfield()
                if formfield:
                    self.fields[field_name] = formfield

        # Устанавливаем значение по умолчанию для города и ресторана
        if self.instance.pk is None and not user.is_superuser:
            set_admin_data(self, user)

        # отображение process_comment
        if self.instance is None or self.instance.process_comment is None:
            self.fields['process_comment'].widget = forms.HiddenInput()

        if not user.is_superuser:
            # self.fields['created'].widget = forms.HiddenInput()
            self.fields['delivery'].widget = FilteredByUserAndCityWidget(
                is_superuser=user.is_superuser,
                city=self.instance.city,
                model_class=Delivery,
            )
            self.fields['courier'].widget = FilteredByUserAndCityWidget(
                                                city=self.instance.city,
                                                is_superuser=user.is_superuser,
                                                model_class=Courier)
            self.fields['delivery_zone'].queryset = get_filtered_delivery_zones(user)

        # Исключаем скидки на 1й заказ (1) и на оплату наличными при доставке (3)
        if 'discount' in self.fields:
            filtered_discounts = [(None, '---------')] + [
                (discount.id, str(discount))
                for discount in Discount.objects.all()
                if discount.id not in [3]
            ]
            self.fields['discount'].choices = filtered_discounts

        # если юзер известен, то загрузка его избранных адресов
        user = self.instance.user
        if 'user' in self.initial:
            user = self.initial['user']
        # при создании нового заказа и ошибке это пусто
        if user:
            user_addresses = UserAddress.objects.filter(base_profile=user)
            choices = [(address.id,
                        (f"{address.address}, кв. {address.flat}, "
                         f"этаж {address.floor}, домофон {address.interfon}")
                        ) for address in user_addresses]
            choices.insert(0, ('', '------------'))
            self.fields['my_delivery_address'].choices = choices

            # Получение координат и передача их в форму
            my_coordinates = {
                str(address.id):
                address.coordinates for address in user_addresses}

            coordinates_json = json.dumps(my_coordinates)
            self.fields['my_address_coordinates'].initial = coordinates_json

            # Получение координат и передача их в форму
            my_address_comments = {
                str(address.id): (
                    f"flat:{address.flat}, "
                    f"floor:{address.floor}, "
                    f"interfon:{address.interfon}"
                ) for address in user_addresses}
            my_address_comments_json = json.dumps(my_address_comments)
            self.fields[
                'my_address_comments'].initial = my_address_comments_json

    class Meta:
        model = Order
        fields = '__all__'

    def get_form(self, request, obj=None, **kwargs):
        """
        Переопределяем метод get_form для передачи пользователя в форму.
        """
        form = super().get_form(request, obj, **kwargs)
        form.user = request.user  # Передаем текущего пользователя в форму
        return form

    # def clean_recipient_name(self):
    #     """Проверка что имя не содержит цифры/символы и пр"""
    #     source = self.data.get('source')
    #     recipient_name = self.data.get('recipient_name')
    #     if source in ['1', '4']:
    #         # если телефон, сайт. В остальных источн поле может быть пустым
    #         if recipient_name is None or recipient_name == '':
    #             raise forms.ValidationError(
    #                 "Укажите имя.")

    #         validate_first_and_last_name(recipient_name)

    #     return recipient_name

    # def clean_recipient_phone(self):
    #     """Проверка форматирования номера телефона"""
    #     source = self.data.get('source')
    #     recipient_phone = self.data.get('recipient_phone')
    #     if source in ['1', '4']:
    #         # если телефон/сайт. В остальных источн поле может быть пустым
    #         if recipient_phone is None or recipient_phone == '':
    #             raise forms.ValidationError(
    #                 "Укажите телефон.")

    #         validate_international_phonenumber(recipient_phone)

    #     return recipient_phone

    def clean_recipient_address(self):
        recipient_address = self.cleaned_data.get('recipient_address')
        if recipient_address:
            # Проверяем, содержит ли адрес только буквы, цифры и пробелы
            if not re.search(r'\d+', recipient_address):
                raise forms.ValidationError("Укажите номер дома.")

        delivery = self.cleaned_data.get('delivery')
        source = self.data.get('source')
        my_delivery_address = self.data.get('my_delivery_address')
        coordinates = self.data.get('coordinates')

        if (delivery is not None and delivery.type == 'delivery'
                and source in ['1', '3', '4']):

            if my_delivery_address not in [None, '']:

                addres_obj = UserAddress.objects.filter(
                    base_profile=self.cleaned_data['user'],
                    id=int(my_delivery_address)
                ).first()

                recipient_address = addres_obj.address
                self.my_delivery_address = addres_obj
                self.coordinates = addres_obj.coordinates
                self.lat, self.lon = parce_coordinates(addres_obj.coordinates)
                self.address_comment = (
                    f"flat: {addres_obj.flat}, "
                    f"floor: {addres_obj.floor}, "
                    f"interfon: {addres_obj.interfon}"
                )

                return recipient_address

            if recipient_address is None or recipient_address == '':
                raise forms.ValidationError(
                    "Проверьте указан ли адрес доставки клиенту.")

            if recipient_address != self.instance.recipient_address:

                try:
                    self.lat, self.lon = parce_coordinates(coordinates)

                except Exception as e:
                    pass

        return recipient_address

    def clean_my_delivery_address(self):
        my_delivery_address = self.cleaned_data['my_delivery_address']
        if my_delivery_address == '':
            return None
        else:
            return self.my_delivery_address

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
                                ("Введенный адрес находится вне зоны "
                                 "обслуживания. Проверьте адрес или внесите "
                                 "вручную зону и цену доставки.")
                            )
                        return new_delivery_zone

                    except AttributeError:
                        raise forms.ValidationError(
                                ("Для введенного адреса невозможно получить "
                                 "координаты и расчитать зону доставки. "
                                 "Проверьте адрес или внесите "
                                 "вручную зону и цену доставки.")
                            )

                else:

                    if delivery_zone.name == 'по запросу':
                        return delivery_zone

                    try:
                        new_delivery_zone = get_delivery_zone(
                            self.cleaned_data.get('city', 'Beograd'),
                            self.lat, self.lon)
                        if new_delivery_zone.name == 'уточнить':
                            raise forms.ValidationError(
                                ("Введенный адрес находится вне зоны "
                                 "обслуживания. Проверьте адрес или внесите "
                                 "вручную зону и цену доставки.")
                            )
                    except AttributeError:
                        raise forms.ValidationError(
                                ("Для введенного адреса невозможно получить "
                                 "координаты и расчитать зону доставки. "
                                 "Проверьте адрес или внесите "
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
        delivery_time = self.cleaned_data.get('delivery_time')

        # Если это существующий заказ (редактирование)
        if self.instance and self.instance.pk:
            # Проверяем, изменилось ли значение поля
            # Сравниваем с исходным значением из БД
            if self.instance.delivery_time == delivery_time:
                # Если значение не изменилось, возвращаем его без валидации
                return delivery_time

        delivery = self.data.get('delivery')
        restaurant = self.cleaned_data.get('restaurant')

        if delivery_time is not None and delivery is not None:
            delivery = Delivery.objects.filter(id=int(delivery)).first()

            if delivery.type == 'takeaway' and restaurant is not None:
                validate_delivery_time(delivery_time, delivery, restaurant)
            else:
                validate_delivery_time(delivery_time, delivery)

        return delivery_time

    def clean_restaurant(self):
        restaurant = self.data.get('restaurant')
        city = self.data.get('city')
        restaurant = Restaurant.objects.get(id=restaurant)
        if restaurant.city != city:
            raise forms.ValidationError(
                "Проверьте соответствие полей Город и Ресторан.")

        return restaurant

    # def clean_payment_type(self):
    #     source = self.data.get('source')
    #     payment_type = self.cleaned_data['payment_type']
    #     if source in ['1', '2', '4']:
    #         if payment_type is None:
    #             raise forms.ValidationError(
    #                 "Укажите способ оплаты.")
    #     return payment_type

    def clean_process_comment(self):
        source = self.data.get('source')
        process_comment = self.cleaned_data['process_comment']
        if source in ['1', '2', '3', '4']:
            if process_comment == '':
                return None
        return process_comment

    def clean(self):
        cleaned_data = super().clean()
        # Удаляем ошибки валидации для поля my_recipient_address
        if 'my_delivery_address' in self._errors:
            del self._errors['my_delivery_address']
            cleaned_data['my_delivery_address'] = self.my_delivery_address
        if not self.user.is_superuser and cleaned_data['restaurant'] != self.user.restaurant:
            raise forms.ValidationError("You cannot edit orders from other restaurants.")

        return cleaned_data

    # def clean(self):
    #     cleaned_data = super().clean()

    #     # Удаляем ошибки валидации для поля my_delivery_address
    #     if 'my_delivery_address' in self._errors:
    #         del self._errors['my_delivery_address']
    #         cleaned_data['my_delivery_address'] = self.my_delivery_address

    #     if not self.user.is_superuser and cleaned_data.get('restaurant') != self.user.restaurant:
    #         raise forms.ValidationError("You cannot edit orders from other restaurants.")

    #     # Проверяем, выключена ли доставка
    #     delivery = cleaned_data.get('delivery')
    #     if delivery and delivery.type != 'delivery':
    #         # Сохраняем значения полей в отдельные атрибуты для использования при необходимости
    #         self._saved_delivery_zone = cleaned_data.get('delivery_zone')
    #         self._saved_delivery_cost = cleaned_data.get('delivery_cost')
    #         self._saved_recipient_address = cleaned_data.get('recipient_address')
    #         self._saved_coordinates = cleaned_data.get('coordinates')
    #         self._saved_address_comment = cleaned_data.get('address_comment')

    #         # Очищаем поля в cleaned_data
    #         cleaned_data['delivery_zone'] = None
    #         cleaned_data['delivery_cost'] = 0
    #         cleaned_data['recipient_address'] = ''
    #         cleaned_data['coordinates'] = ''
    #         cleaned_data['address_comment'] = ''

    #     return cleaned_data

    # ВОЗМОЖНО ЭТО НЕ НУЖНО! т.к. вызывается один раз в admin.save_model()
    # НО В ADD нужно, т.к. там вызывается еще раз сейф
    def save(self, commit=True):
        """
        Включаем режим редактирования админом перед сохранением
        """
        instance = super().save(commit=False)  # Всегда получаем несохраненный экземпляр

        if self.cleaned_data.get('created_by') is None:
            instance.created_by = 2

        # Всегда сохраняем с флагом is_admin_mode=True
        instance.save(is_admin_mode=True)

        if commit and hasattr(self, 'save_m2m'):
            self.save_m2m()

        return instance


class OrderChangelistForm(forms.ModelForm):
    payment_type = forms.ChoiceField(
        choices=settings.PAYMENT_METHODS,  # Ваши варианты оплаты
        widget=forms.Select(),    # Выпадающий список
        required=False
    )

    status = forms.ChoiceField(
        choices=[
            ('WCO', 'Ожид подтв'),    # Ожидает подтверждения
            ('CFD', 'Подтв'),         # Подтвержден
            ('RDY', 'Готов'),
            ('OND', 'Отправлен'),    # Отправлен
            ('CND', 'Отмен'),         # Отменен
        ],
        widget=forms.Select(),
        required=False
    )

    class Meta:
        model = Order
        fields = ['status', 'invoice', 'courier', 'payment_type']

    def __init__(self, *args, **kwargs):
        # Получаем объект запроса (request), чтобы проверить, является ли пользователь суперпользователем
        request = kwargs.pop('request')
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            # Отключаем/фильтруем поле courier.
            # Если самовывоз, то отключаем совсем.
            # Если доставка, то выбираем курьеров по городу или все курьеры, если суперпользователь
            if self.instance.delivery.type == 'takeaway':
                self.fields['courier'].widget = forms.HiddenInput()
            else:
                city = self.instance.city
                  # Проверяем, является ли текущий пользователь суперпользователем
                is_superuser = request.user.is_superuser
                # Применяем кастомный виджет для поля courier
                self.fields['courier'].widget = FilteredByUserAndCityWidget(
                                                    city=city,
                                                    is_superuser=is_superuser,
                                                    model_class=Courier)

            # Отключаем поле payment_type, если источник партнер
            # if self.instance.source in settings.PARTNERS_LIST:
            #     if self.instance.source != 'P2-2':
            #         self.fields['payment_type'].widget = forms.HiddenInput()
            #         # Не та дверь идет без чека, поэтому оставим для визуальной проверки
            #         self.fields['invoice'].widget = forms.HiddenInput()
            #     else:
            #         self.fields['payment_type'].widget.attrs['disabled'] = 'disabled'

def set_admin_data(self, user):
    pass


class BasePartnerOrderForm(forms.ModelForm):
    source_id = forms.CharField(
        label='ID источника',
        required=True)
    # поле сделано обязательным

    order_type = forms.ChoiceField(
        choices=settings.ORDER_TYPES,
        label='Тип заказа',
        initial='T'  # Default to Delivery
    )

    class Meta:
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        order_type = self.get_source_code()
        self.fields['order_type'].widget = forms.HiddenInput()
        self.fields['order_type'].initial = self.get_source_code()

        if order_type == 'P2-1':
            self.fields['invoice'].initial = False
        # Заказы Smoke по умолчанию без чека

        if self.instance.pk is None and not self.user.is_superuser:
            set_admin_data(self, self.user)




    def clean(self):
        cleaned_data = super().clean()
        source = self.get_source_code()
        delivery = Delivery.objects.get(
            city=self.user.city,
            type='takeaway'
        )
        cleaned_data.update({
            'source': source,
            'delivery': delivery,
            'created_by': 2,
            'status': 'CFD'
        })

        self.instance.source = source
        self.instance.created_by = 2
        self.instance.delivery = delivery
        self.instance.restaurant = self.user.restaurant
        self.instance.city = self.user.city
        self.instance.status = 'CFD'

        return cleaned_data

    def get_source_code(self):
        """Должен быть переопределен в дочерних классах"""
        raise NotImplementedError


class OrderGlovoAdminForm(BasePartnerOrderForm):
    class Meta(BasePartnerOrderForm.Meta):
        model = OrderGlovoProxy

    def get_source_code(self):
        return 'P1-1'


class OrderWoltAdminForm(BasePartnerOrderForm):
    class Meta(BasePartnerOrderForm.Meta):
        model = OrderWoltProxy

    def get_source_code(self):
        return 'P1-2'


class OrderSmokeAdminForm(BasePartnerOrderForm):
    class Meta(BasePartnerOrderForm.Meta):
        model = OrderSmokeProxy

    def get_source_code(self):
        return 'P2-1'


class OrderNeTaDverAdminForm(BasePartnerOrderForm):
    class Meta(BasePartnerOrderForm.Meta):
        model = OrderNeTaDverProxy

    def get_source_code(self):
        return 'P2-2'


class OrderSealTeaAdminForm(BasePartnerOrderForm):
    class Meta(BasePartnerOrderForm.Meta):
        model = OrderSealTeaProxy

    def get_source_code(self):
        return 'P3-1'
