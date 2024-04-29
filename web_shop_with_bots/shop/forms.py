import json
from urllib.parse import urlencode

from django import forms
from django.contrib import admin
from django.forms.widgets import TextInput
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from delivery_contacts.models import Delivery
from delivery_contacts.services import get_delivery_zone
from delivery_contacts.utils import (google_validate_address_and_get_coordinates, parce_coordinates)
from shop.models import Order
from shop.validators import (validate_delivery_time,
                             validate_flat)
from users.models import UserAddress
from tm_bot.services import send_message_new_order
import re
import json


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


class OrderAdminForm(forms.ModelForm):
    recipient_address = forms.CharField(
               label='Адрес доставки',
               required=False,
               widget=forms.TextInput(attrs={'size': '40',
                                             'autocomplete': 'on',
                                             'class': 'basicAutoComplete',
                                             'style': 'width: 50%;'}))

    my_delivery_address = forms.ChoiceField(
        label='Мои адреса',
        required=False,
        choices=[]
        # label='Мои адреса',
        # required=False,
        # choices=[],
        # # Пустой список, так как варианты будут добавляться динамически из JS
        # widget=forms.Select(attrs={'class': 'basicAutoComplete',
        #                            'style': 'width: 50%;'}),
        # # Вы можете изменить виджет по своему усмотрению
    )

    # address_comment = forms.CharField(widget=forms.HiddenInput(),
    #                                       required=False)
    my_address_coordinates = forms.CharField(widget=forms.HiddenInput(),
                                          required=False)
    auto_delivery_zone = forms.CharField(label='Зона доставки (автом)',
                                         required=False)
    auto_delivery_cost = forms.DecimalField(label='Стоимость доставки (автом)',
                                            required=False,
                                            decimal_places=2)
    calculate_delivery_button = forms.CharField(
        label='Рассчитать стоимость доставки.',
        widget=forms.TextInput(attrs={'type': 'button',
                                      'value': 'Рассчитать',
                                      'data-error': 'calculate-delivery-error'}),
        required=False,
        help_text=(
            "Если результат = 'zone1/zone2/zone3', то поля   "
            "'ЗОНА ДОСТАВКИ, СТОИМОСТЬ ДОСТАВКИ'   можно не заполнять.<br>"
            "Если результат рассчета 'УТОЧНИТЬ', то нужно:<br>"
            " - уточнить адрес;<br>"
            " - выбрать вручную одну из 'zone1/zone2/zone3';<br>"
            " - выбрать зону 'по запросу' и вручную внести стоимость доставки."
            )
    )
    error_message = forms.CharField(
        label='ошибка',
        widget=forms.TextInput(attrs={'style': 'font-size: small; color: red; display: none; width: 900px;'}),
        required=False
    )
    calc_message = forms.CharField(
        label='комм.',
        widget=forms.TextInput(attrs={'style': 'font-size: small; color: red; display: none; width: 900px;'}),
        required=False
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
        user = self.instance.user if self.instance.pk else None
        if 'user' in self.initial:
            user = self.initial['user']
        # при создании нового заказа и ошибке это пусто
        if user:
            user_addresses = UserAddress.objects.filter(base_profile=user)
            choices = [(address.id, f"{address.address}, кв. {address.flat}, этаж {address.floor}, домофон {address.interfon}") for address in user_addresses]
            choices.insert(0, ('', '------------'))
            self.fields['my_delivery_address'].choices = choices

            # Получение координат и передача их в форму
            my_coordinates = {str(address.id): address.coordinates for address in user_addresses}
            coordinates_json = json.dumps(my_coordinates)
            self.fields['my_address_coordinates'].initial = coordinates_json

    class Meta:
        model = Order
        fields = '__all__'

    def clean_recipient_address(self):
        recipient_address = self.cleaned_data.get('recipient_address')
        if recipient_address:
            # Проверяем, содержит ли адрес только буквы, цифры и пробелы
            if not re.search(r'\d+', recipient_address):
                raise forms.ValidationError("Укажите номер дома.")

        delivery = self.cleaned_data.get('delivery')

        my_delivery_address = self.data.get('my_delivery_address')
        coordinates = self.data.get('coordinates')

        if delivery is not None and delivery.type == 'delivery':

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
                                ("Введенный адрес находится вне зоны обслуживания."
                                 "Проверьте адрес или внесите вручную зону и цену доставки.")
                            )
                        return new_delivery_zone

                    except AttributeError:
                        raise forms.ValidationError(
                                ("Для введенного адреса невозможно получить координаты "
                                 "и расчитать зону доставки. Проверьте адрес или внесите "
                                 "вручную зону и цену доставки.")
                            )

                elif delivery_zone.name in ['zone1', 'zone2', 'zone3',
                                            'по запросу', 'уточнить']:

                    if delivery_zone.name == 'по запросу':
                        return delivery_zone

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

    def clean(self):
        cleaned_data = super().clean()
        # Удаляем ошибки валидации для поля my_recipient_address
        if 'my_recipient_address' in self._errors:
            del self._errors['my_recipient_address']

        # if cleaned_data['recipient_address'] != self.instance.recipient_address:

            # delivery = cleaned_data.get('delivery')
            # if delivery is not None and delivery.type == 'delivery':
            #     flat = cleaned_data.get('flat')
            #     floor = cleaned_data.get('floor')
            #     interfon = cleaned_data.get('interfon')
            #     cleaned_data['address_comment'] = f"flat: {flat}, floor: {floor}, interfon: {interfon}"

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get('created_by') is None:
            instance.created_by = 2

        if commit:
            instance.save()

        return instance
