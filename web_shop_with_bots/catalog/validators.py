from .models import Dish
from django.core.exceptions import ValidationError


def validator_dish_exists_active(value):
    if Dish.objects.filter(article=value, is_active=True).exists() is None:
        raise ValidationError(
            "Currently selected dish is unavailable for ordering.")
