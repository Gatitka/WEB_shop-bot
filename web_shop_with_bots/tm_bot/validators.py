import re

import phonenumbers
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def get_msgr_data_validated(attrs):
    # Проверяем, что оба поля заполнены
    msngr_type, msngr_username = attrs.get('msngr_type'), attrs.get('msngr_username')

    if msngr_type is not None or msngr_username is not None:
        # Если одно из полей заполнено, а другое нет, вызываем исключение
        if msngr_type in [None, ''] or msngr_username in [None, '']:
            raise ValidationError(
                "Both 'msngr_username' and 'msngr_type' must be filled.")

    validate_msngr_type_username_full(msngr_type, msngr_username)


def validate_msngr_type_username_full(msngr_type, msngr_username):
    if msngr_type not in ['tm', 'wts']:
        raise ValidationError(
            "Msngr_type not 'tm'/'wts'.")

    if msngr_type == 'tm':
        # Проверка на допустимые символы
        # (A-z, 0-9, и подчеркивания)
        if not re.match("^@[A-Za-z0-9_]+$", msngr_username):
            raise ValidationError(
                "TM username must start with '@' or contains invalid symbols."
            )

            # Проверка длины (5-32 символа)
        if not (5 <= len(msngr_username) <= 32):
            raise ValidationError("TM username from 5 to 32 symbols.")

    elif msngr_type == 'wts':
        try:
            parsed_phone = phonenumbers.parse(msngr_username, None)
            if not phonenumbers.is_valid_number(parsed_phone):
                raise ValidationError("Wts username must start with '+' or invalid phone number.")
        except Exception:
            raise ValidationError("Wts username must start with '+' or invalid phone number.")




def validate_messenger_account(value):
    if value:
        messenger = value
        if not isinstance(value, dict):
            raise ValidationError(
                "Messenger data is not a dictionary.")

        if 'msngr_type' not in messenger:
            raise ValidationError({
                "msngr_type":
                    ["Msngr_type is missing."]})

        if 'msngr_username' not in messenger:
            raise ValidationError({
                "msngr_username":
                    "Msngr_username is missing."})


def validate_msngr_type(value):
    if value not in ['tm', 'wts']:
        raise ValidationError(
            "Msngr_type not 'tm'/'wts'.")


def validate_msngr_username(value):
    if value:
        msngr_type = value[0]

        if msngr_type not in ['+', '@']:
            raise ValidationError(_(
                "Username должен начинаться с '+' или '@'."))

        if msngr_type == '@':
            # Проверка на допустимые символы Telegram
            # (A-z, 0-9, и подчеркивания)
            if not re.match("^@[A-Za-z0-9_]+$", value):
                raise ValidationError(_(
                    "Недопустимые символы в Telegram username."
                    " Username должен начинаться с @ и содержать "
                    "только цифры и буквы."
                ))

                # Проверка длины (5-32 символа)
            if not (5 <= len(value) <= 32):
                raise ValidationError(
                    "Длина Telegram username должна быть"
                        " от 5 до 32 символов."
                    )

        elif msngr_type == '+':
            # Проверка на допустимые символы WhatsApp
            try:
                parsed_phone = phonenumbers.parse(value, None)
                if not phonenumbers.is_valid_number(parsed_phone):
                    raise ValidationError(_(
                        "Неверный формат номера телефона."))
                msngr_type = 'wts'
            except Exception:
                raise ValidationError(_(
                            "Неверный формат номера телефона."))
