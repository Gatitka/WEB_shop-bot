from shop.models import Order
from delivery_contacts.utils import (
    google_validate_address_and_get_coordinates)
from django import forms
from delivery_contacts.models import Delivery
from delivery_contacts.services import get_delivery_zone
from shop.validators import validate_delivery_time
from users.models import UserAddress


from django.forms.widgets import TextInput
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from urllib.parse import urlencode
from django.contrib import admin
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


# class ForeignKeyRawIdWidget(TextInput):
#     """
#     A Widget for displaying ForeignKeys in the "raw_id" interface rather than
#     in a <select> box.
#     """
#     template_name = 'admin/widgets/foreign_key_raw_id.html'

#     def __init__(self, rel, admin_site, attrs=None, using=None):
#         self.rel = rel
#         self.admin_site = admin_site
#         self.db = using
#         super().__init__(attrs)

#     def get_context(self, name, value, attrs):
#         context = super().get_context(name, value, attrs)
#         rel_to = self.rel.model
#         if rel_to in self.admin_site._registry:
#             # The related object is registered with the same AdminSite
#             related_url = reverse(
#                 'admin:%s_%s_changelist' % (
#                     rel_to._meta.app_label,
#                     rel_to._meta.model_name,
#                 ),
#                 current_app=self.admin_site.name,
#             )

#             params = self.url_parameters()
#             if params:
#                 related_url += '?' + urlencode(params)
#             context['related_url'] = related_url
#             context['link_title'] = _('Lookup')
#             # The JavaScript code looks for this class.
#             context['widget']['attrs'].setdefault('class',
#                                                   'vForeignKeyRawIdAdminField')
#         else:
#             context['related_url'] = None
#         if context['widget']['value']:
#             context['link_label'], context['link_url'] = (
#                 self.label_and_url_for_value(value))
#         else:
#             context['link_label'] = None

#         # Добавляем атрибут для отслеживания изменений в поле ввода
#         context['widget']['attrs']['onchange'] = 'updateUserFields()'

#         return context

#     def label_and_url_for_value(self, value):
#         # формирование кликабельной ссылки с именем после добавления юзера
#         try:
#             obj = self.rel.model._default_manager.using(self.db).get(pk=value)
#             return obj, f'<a href="{obj.get_absolute_url()}">{obj}</a>'
#         except self.rel.model.DoesNotExist:
#             return '', ''

#     def base_url_parameters(self):
#         limit_choices_to = self.rel.limit_choices_to
#         if callable(limit_choices_to):
#             limit_choices_to = limit_choices_to()
#         return url_params_from_lookup_dict(limit_choices_to)

#     def url_parameters(self):
#         from django.contrib.admin.views.main import TO_FIELD_VAR
#         params = self.base_url_parameters()
#         params.update({TO_FIELD_VAR: self.rel.get_related_field().name})
#         return params


class OrderAdminForm(forms.ModelForm):
    recipient_address = forms.CharField(
               required=False,
               widget=forms.TextInput(attrs={'size': '40',
                                             'autocomplete': 'on',
                                             'class': 'basicAutoComplete',
                                             'style': 'width: 50%;'}))

    my_recipient_address = forms.ChoiceField(
        required=False,
        choices=[],
        # Пустой список, так как варианты будут добавляться динамически из JS
        widget=forms.Select(attrs={'class': 'basicAutoComplete',
                                   'style': 'width: 50%;'}),
        # Вы можете изменить виджет по своему усмотрению
    )

    address_coordinates = forms.CharField(widget=forms.HiddenInput(),
                                          required=False)
    auto_delivery_zone = forms.CharField(label='Зона доставки (автом)',
                                         required=False)
    auto_delivery_cost = forms.DecimalField(label='Стоимость доставки (автом)',
                                            required=False,
                                            decimal_places=2)
    calculate_delivery_button = forms.CharField(
        label='Рассчитать стоимость доставки',
        widget=forms.TextInput(attrs={'type': 'button', 'value': 'Рассчитать'}),
        required=False
    )

    # user = forms.CharField(
    #     required=False,
    #     widget=ForeignKeyRawIdWidget(
    #         Order._meta.get_field('user').remote_field,
    #         admin.site)
    # )

    class Meta:
        model = Order
        fields = '__all__'

    def clean_recipient_address(self):
        delivery = self.cleaned_data.get('delivery')
        recipient_address = self.cleaned_data.get('recipient_address')
        my_recipient_address = self.data.get('my_recipient_address')
        address_coordinates = self.data.get('address_coordinates')

        if delivery is not None and delivery.type == 'delivery':

            if my_recipient_address not in [None, '']:
                recipient_address = my_recipient_address

                coordinates_dict = json.loads(address_coordinates)
                lat = coordinates_dict.get('lat')
                lon = coordinates_dict.get('lon')
                if lat and lon:
                    self.lat, self.lon = float(lat), float(lon)

                return recipient_address

            if recipient_address is None or recipient_address == '':
                raise forms.ValidationError(
                    "Проверьте указан ли адрес доставки клиенту.")

            if recipient_address != self.instance.recipient_address:

                try:
                    lat, lon, status = (
                        google_validate_address_and_get_coordinates(
                            recipient_address
                        )
                    )
                    self.lat = lat
                    self.lon = lon

                except Exception as e:
                    pass

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
        return cleaned_data

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
