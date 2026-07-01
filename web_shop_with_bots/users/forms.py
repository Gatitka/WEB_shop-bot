from django import forms
from .models import BaseProfile, WEBAccount
from django.core.exceptions import ValidationError
from .validators import validate_first_and_last_name


class BaseProfileAdminForm(forms.ModelForm):

    first_web_order = forms.ChoiceField(
            choices=((True, 'Да'), (False, 'Нет')),
            widget=forms.RadioSelect,
            label='Первый заказ на сайте',
            help_text=(
                "да - заказы на сайте есть, "
                "скидка на 1й заказ НЕ действительна<br>"
                "нет - заказов на сайте НЕТ, "
                "скидка на 1й заказ действительна<br>"
            )
        )

    class Meta:
        model = BaseProfile
        fields = '__all__'


class WEBAccountAdminForm(forms.ModelForm):

    class Meta:
        model = WEBAccount
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.instance есть всегда; для новых obj.pk is None
        if self.instance and self.instance.is_dummy_telegram:
            self.fields['first_name'].required = False
            self.fields['last_name'].required = False

    def clean_first_name(self):
        value = self.cleaned_data.get('first_name', '')
        if not value and self.instance and self.instance.is_dummy_telegram:
            return value  # пустое — ok, выходим до валидатора
        validate_first_and_last_name(value)  # "me", цифры — всё ещё запрещено
        return value

    def clean_last_name(self):
        value = self.cleaned_data.get('last_name', '')
        if not value and self.instance and self.instance.is_dummy_telegram:
            return value  # пустое — ok, выходим до валидатора
        validate_first_and_last_name(value)  # "me", цифры — всё ещё запрещено
        return value
