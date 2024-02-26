from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from datetime import date, datetime, timedelta


def validate_first_and_last_name(value):
    if not value:
        raise ValidationError(_('Please provide the last name.'),
                              code='invalid')
    if value.lower() in ['me', 'i', 'я', 'ja', 'и'] or not value.isalpha():
        raise ValidationError(_('Please check your name, note that only letters are allowed.'),
                              code='invalid')


def validate_birthdate(value):
    min_birthdate = datetime.now().date() - timedelta(days=365*100)
    if value < min_birthdate:
        raise ValidationError(_('Проверьте, что дата рождения не ранее 100 назад.'),
                              code='invalid')

    today = date.today()
    if today <= value:
        raise ValidationError(_("Проверьте, что дата рождения не в будущем"),
                              code='invalid')
