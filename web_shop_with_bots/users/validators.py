from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_first_and_last_name(value):
    if not value:
        raise ValidationError(_('Please, provide the last name.'),
                              code='invalid')
    if value.lower() in ['me', 'i', 'я', 'ja', 'и'] or not value.isalpha():
        raise ValidationError(_('Please check your name, note that only letters are allowed.'),
                              code='invalid')


def validate_birthdate(value):
    min_birthdate = datetime.now().date() - timedelta(days=365*100)
    if value < min_birthdate:
        raise ValidationError(_('Birthdate is more than 100 years ago.'),
                              code='invalid')

    today = date.today()
    if today <= value:
        raise ValidationError(_("Birthdate is in future."),
                              code='invalid')


class AlphanumericPasswordValidator:
    def validate(self, password, user=None):
        if (not any(char.isdigit() for char in password)
            or not any(char.isalpha() for char in password)):
            raise ValidationError(
                _("Password must contain at least one letter and one digit."),
                code='invalid_password',
            )

    def get_help_text(self):
        return _(
            "Your password must contain at least one letter and one digit."
        )
