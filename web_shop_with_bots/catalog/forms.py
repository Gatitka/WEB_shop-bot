from django import forms
from django.core.exceptions import ValidationError
from .models import Dish
from parler.forms import TranslatableModelForm

class DishAdminForm(TranslatableModelForm):
    class Meta:
        model = Dish
        fields = "__all__"

    def clean_category(self):
        cats = self.cleaned_data.get("category")
        if not cats or cats.count() == 0:
            raise ValidationError("Выберите хотя бы одну категорию.")
        return cats


class DishPricesUploadForm(forms.Form):
    file = forms.FileField(label="Excel файл с ценами")
