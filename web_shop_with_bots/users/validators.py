from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings


def validate_first_and_last_name(value):
    if not value:
        raise ValidationError(_('Please, provide the last name.'),
                              code='invalid')
    if (value.lower() in ['me', 'i', 'я', 'ja', 'и', 'name', 'имя', 'ime']
            or not value.replace(' ', '').isalpha()):

        raise ValidationError(_("Please check your name, "
                                "note that only letters are allowed."),
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


def validate_language(value):
    if value is not None:
        valid_languages = [language[0] for language in settings.LANGUAGES]
        if value in valid_languages:
            return value
    return settings.DEFAULT_CREATE_LANGUAGE


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


def coordinates_validator(coordinates):
    if coordinates is not None:
        if not isinstance(coordinates, str):
            raise ValidationError(_("Input should be a string"))

        try:
            parts = coordinates.split(', ')
            if len(parts) != 2:
                raise ValidationError(_("Input string should contain two parts separated by ', '."))

            latitude = float(parts[0])
            longitude = float(parts[1])

        except ValueError:
            raise ValidationError(_("Both parts of the input string should be convertible to float."))

        if not (44 <= latitude <= 46):
            raise ValidationError(_("Latitude should be between 44 and 46 degrees."))

        if not (19 <= longitude <= 22):
            raise ValidationError(_("Longitude should be between 19 and 22 degrees."))


# 19.464173820140182
# 21.249452070450054

# 45.6370791312015,
# 44.51678371302423,
