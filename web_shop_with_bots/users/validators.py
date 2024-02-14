from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_first_and_last_name(value):
    if not value:
        raise ValidationError(_('Please provide the last name.'),
                              code='invalid')
    if value.lower() in ['me', 'i', 'я', 'ja', 'и'] or not value.isalpha():
        raise ValidationError(_('Please check your name, note that only letters are allowed.'),
                              code='invalid')
