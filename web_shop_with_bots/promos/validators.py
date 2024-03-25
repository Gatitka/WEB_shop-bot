from .models import Promocode
from django.core.exceptions import ValidationError


def validator_promocode(value):
    if value is not None:
        if not Promocode.is_valid(value):
            raise ValidationError(
                "Please check the promocode.")
