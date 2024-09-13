from django import forms
from .models import BaseProfile


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
