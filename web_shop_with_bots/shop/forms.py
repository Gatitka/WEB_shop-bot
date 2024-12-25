import json
from django.conf import settings
from django import forms

from delivery_contacts.models import Delivery, Courier, Restaurant
from delivery_contacts.services import get_delivery_zone
from delivery_contacts.utils import parce_coordinates
from shop.models import (Order, OrderGlovoProxy, OrderWoltProxy,
                         OrderSmokeProxy, DeliveryZone, Delivery)
from shop.validators import (validate_delivery_time)
from phonenumber_field.validators import validate_international_phonenumber
from users.models import UserAddress
from users.validators import validate_first_and_last_name
from tm_bot.services import send_message_new_order
import re
from django.forms.widgets import Select
from django.db.models import Q


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


class CourierByCityWidget(Select):
    """
    Кастомный виджет для поля courier, который фильтрует курьеров по городу заказа.
    Если пользователь суперпользователь, показываются все курьеры.
    """
    def __init__(self, city, is_superuser, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.city = city
        self.is_superuser = is_superuser

    def get_context(self, name, value, attrs):
        # Если пользователь суперпользователь, показываем всех курьеров
        self.choices = [(None, '--------')]  # Опция для None
        if self.is_superuser:
            queryset = Courier.objects.all()
            self.choices += [(courier.id, str(courier)) for courier in queryset]
        else:
            # Иначе фильтруем курьеров по городу
            queryset = Courier.objects.filter(city=self.city)
            self.choices += [(courier.id, courier.name) for courier in queryset]
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


def get_filtered_delivery(user):
    # Базовый запрос для всех пользователей
    if user.is_superuser:
        return Delivery.objects.all()
    else:
        # Получаем города, к которым у пользователя есть доступ
        user_cities = user.restaurant.city
        user_query = Q(city=user_cities)
        return Delivery.objects.filter(user_query).distinct()


class OrderAdminForm(forms.ModelForm):
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
        help_text=(
            "Если zone определяется (прим. zone3), то поля   "
            "'ЗОНА ДОСТАВКИ, СТОИМОСТЬ ДОСТАВКИ'   можно не заполнять.<br><br>"
            "Если результат = 'УТОЧНИТЬ', то нужно:<br>"
            " - уточнить адрес;<br>"
            " - выбрать вручную одну из zone;<br>"
            " - выбрать зону 'ПО ЗАПРОСУ' и вручную внести стоимость доставки.<br><br>"
            "Для сохранения нестандартной стоимости в стандартной зоне, "
            "смените зону на 'ПО ЗАПРОСУ' и внесите свою стоимость."
            )
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
        # Устанавливаем значение по умолчанию для города и ресторана
        if self.instance.pk is None and not user.is_superuser:
            set_admin_data(self, user)

        # отображение process_comment
        if self.instance is None or self.instance.process_comment is None:
            self.fields['process_comment'].widget = forms.HiddenInput()

        if self.instance.pk and not user.is_superuser:
            self.fields['delivery_zone'].queryset = get_filtered_delivery_zones(user)
            self.fields['delivery'].queryset = get_filtered_delivery(user)
            self.fields['courier'].widget = CourierByCityWidget(city=self.instance.city,
                                                                is_superuser=user.is_superuser)

        # отображение способов платежа для заказа
        if 'payment_type' in self.fields:
            excluded_methods = ['partner']  # Список методов, которые исключить
            filtered_payment_methods = [
                method for method in settings.PAYMENT_METHODS if method[0] not in excluded_methods]
            filtered_payment_methods.insert(0, (None, '---------'))
            self.fields['payment_type'].choices = filtered_payment_methods

        # выбор курьера только для доставки
        # if self.instance and self.instance.delivery.type == 'takeaway':
        #     self.fields['courier'].widget = forms.HiddenInput()
        # else:
        #     self.fields['courier'].queryset = Courier.objects.filter(
        #                                                     is_active=True)

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

    def clean_recipient_name(self):
        source = self.data.get('source')
        recipient_name = self.data.get('recipient_name')
        if source in ['1', '4']:
            # если телефон, сайт. В остальных источн поле может быть пустым
            if recipient_name is None or recipient_name == '':
                raise forms.ValidationError(
                    "Укажите имя.")

            validate_first_and_last_name(recipient_name)

        return recipient_name

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

    def clean_recipient_phone(self):
        source = self.data.get('source')
        recipient_phone = self.data.get('recipient_phone')
        if source in ['1', '4']:
            # если телефон/сайт. В остальных источн поле может быть пустым
            if recipient_phone is None or recipient_phone == '':
                raise forms.ValidationError(
                    "Укажите телефон.")

            validate_international_phonenumber(recipient_phone)

        return recipient_phone

    def clean_restaurant(self):
        restaurant = self.data.get('restaurant')
        city = self.data.get('city')
        restaurant = Restaurant.objects.get(id=restaurant)
        if restaurant.city != city:
            raise forms.ValidationError(
                "Проверьте соответствие полей Город и Ресторан.")

        return restaurant

    def clean_payment_type(self):
        source = self.data.get('source')
        payment_type = self.cleaned_data['payment_type']
        if source in ['1', '4']:
            if payment_type is None:
                raise forms.ValidationError(
                    "Укажите способ оплаты.")
        return payment_type

    def clean_process_comment(self):
        source = self.data.get('source')
        process_comment = self.cleaned_data['process_comment']
        if source in ['1', '3', '4']:
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

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get('created_by') is None:
            instance.created_by = 2

        if commit:
            instance.save()

        return instance


class OrderChangelistForm(forms.ModelForm):
    payment_type = forms.ChoiceField(
        choices=settings.PAYMENT_METHODS,  # Ваши варианты оплаты
        widget=forms.Select(),    # Выпадающий список
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
            city = self.instance.city
            is_superuser = request.user.is_superuser  # Проверяем, является ли текущий пользователь суперпользователем
            # Применяем кастомный виджет для поля courier
            self.fields['courier'].widget = CourierByCityWidget(city=city,
                                                                is_superuser=is_superuser)

        # Отключаем поле payment_type, если источник - Glovo
        if self.instance and self.instance.source == 'P1-1':
            self.fields['payment_type'].widget.attrs['disabled'] = 'disabled'


class OrderGlovoAdminForm(forms.ModelForm):
    class Meta:
        model = OrderGlovoProxy
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['source'] = 'P1-1'
        cleaned_data['delivery'] = None
        cleaned_data['payment_type'] = 'partner'
        cleaned_data['created_by'] = 2
        self.instance.source = 'P1-1'
        self.instance.delivery = Delivery.objects.get(
                                            city=settings.DEFAULT_CITY,
                                            type='takeaway')
        self.instance.payment_type = 'partner'
        self.instance.created_by = 2
        self.instance.restaurant = self.user.restaurant
        try:
            if self.user.restaurant.city:
                self.instance.city = self.user.restaurant.city
        except Restaurant.DoesNotExist:
            self.instance.city = self.user.city

        return cleaned_data

    def __init__(self, *args, **kwargs):
        user = self.user
        super().__init__(*args, **kwargs)

        # Устанавливаем значение по умолчанию для города и ресторана
        if self.instance.pk is None and not user.is_superuser:
            set_admin_data(self, user)


class OrderWoltAdminForm(forms.ModelForm):
    class Meta:
        model = OrderWoltProxy
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['source'] = 'P1-2'
        cleaned_data['delivery'] = None
        cleaned_data['payment_type'] = 'partner'
        cleaned_data['created_by'] = 2
        self.instance.source = 'P1-2'
        self.instance.delivery = Delivery.objects.get(
                                            city=settings.DEFAULT_CITY,
                                            type='takeaway')
        self.instance.payment_type = 'partner'
        self.instance.created_by = 2

        return cleaned_data

    def __init__(self, *args, **kwargs):
        user = self.user
        super().__init__(*args, **kwargs)

        # Устанавливаем значение по умолчанию для города и ресторана
        if self.instance.pk is None and not user.is_superuser:
            set_admin_data(self, user)


class OrderSmokeAdminForm(forms.ModelForm):
    class Meta:
        model = OrderSmokeProxy
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['source'] = 'P2-1'
        cleaned_data['delivery'] = None
        cleaned_data['payment_type'] = 'partner'
        cleaned_data['created_by'] = 2
        self.instance.source = 'P2-1'
        self.instance.delivery = Delivery.objects.get(
                                            city=settings.DEFAULT_CITY,
                                            type='takeaway')
        self.instance.payment_type = 'partner'
        self.instance.created_by = 2

        return cleaned_data

    def __init__(self, *args, **kwargs):
        user = self.user
        super().__init__(*args, **kwargs)

        # Устанавливаем значение по умолчанию для города и ресторана
        if self.instance.pk is None and not user.is_superuser:
            set_admin_data(self, user)


def set_admin_data(self, user):
    pass
