from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from datetime import datetime


def validate_first_and_last_name(value):
    if not value:
        raise ValidationError(_('Please provide the last name.'),
                              code='invalid')
    if value.lower() in ['me', 'i', 'я', 'ja', 'и'] or not value.isalpha():
        raise ValidationError(_('Please check your name, note that only letters are allowed.'),
                              code='invalid')


def validate_birthdate(value):
    if not value:
        raise ValidationError(_('Please provide the birthdate.'), code='invalid')

    try:
        birthdate = datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        raise ValidationError(_('Invalid birthdate format. Please use the format YYYY-MM-DD.'), code='invalid')

    min_birthdate = datetime.now().replace(year=datetime.now().year - 100)
    if birthdate > min_birthdate:
        raise ValidationError(_('Birthdate should be at least 100 years ago.'), code='invalid')
