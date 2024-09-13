from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from .models import Dish


def validator_dish_exists_active(value):
    if value is not None:
        if not value.isdigit():
            raise ValidationError({
                "detail":"PK must be a number.",
                "code": "invalid",
                "pk": value})

        dish = Dish.objects.filter(article=int(value)).first()
        if not dish:
            raise serializers.ValidationError({
                "detail": "There's no such dish in our menu.",
                "code": "invalid",
                "pk": value})
        if not dish.is_active:
            raise serializers.ValidationError({
                "detail": "We are sorry, but this dish is "
                            "currently inavailable.",
                "code": "invalid",
                "pk": value})


def get_dish_validate_exists_active(value, city, restaurant):
    if value is not None:
        if not value.isdigit():
            raise ValidationError({
                "detail": "PK must be a number.",
                "code": "invalid",
                "pk": value})

    dish = Dish.objects.filter(article=value).prefetch_related(
        'citydishlist_set', 'restaurantdishlist_set'
    ).first()

    # Проверяем, есть ли такие блюда вообще
    if not dish:
        raise ValidationError({
            "detail": "There's no such dish in our menu.",
            "code": "invalid",
            "pk": value
        })

    if restaurant is None:
        # Проверяем, есть ли блюдо в указанном городе
        if (not dish.citydishlist_set.filter(city=city).exists()
            or not dish.is_active):

            raise ValidationError({
                "detail": "We are sorry, but this dish is currently inavailable.",
                "code": "invalid",
                "pk": value
            })

    # Если ресторан указан, проверяем доступность блюда в конкретном ресторане
    else:
        if (not dish.restaurantdishlist_set.filter(restaurant=restaurant).exists()
            or not dish.is_active):

            raise ValidationError({
                "detail": "We are sorry, but this dish is currently inavailable.",
                "code": "invalid",
                "pk": value
            })

    return dish
