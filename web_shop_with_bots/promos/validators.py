from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers
from .models import Promocode
from django.utils.translation import gettext_lazy as _


def validator_promocode(value):
    if value is not None:
        if not Promocode.is_active_wthn_timespan(value):
            raise ValidationError(
                "Please check the promocode.")


def get_promocode_validate_active_in_timespan(value):
    now = timezone.now()
    promocode = Promocode.objects.filter(
        code=value,
        is_active=True,
        valid_from__lte=now,
        valid_to__gte=now
    ).first()

    if not promocode:
        raise serializers.ValidationError({
            "detail": _("Please check the promocode."),
            "code": "invalid"
        })

    return promocode
