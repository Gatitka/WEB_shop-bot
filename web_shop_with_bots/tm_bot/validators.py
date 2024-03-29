from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re

import phonenumbers


# def validate_msngr_account_full(value):
#     if value:
#         messenger = value
#         if not isinstance(value, dict):
#             raise ValidationError(_(
#                 "объект messenger не является словарем"))

#         if 'msngr_type' not in messenger:
#             raise ValidationError(_(
#                 "Ключа msngr_type нет в передаваемом словаре messenger."))

#         if 'msngr_username' not in messenger:
#             raise ValidationError(_(
#                 "Ключа msngr_username нет в передаваемом словаре messenger."))

#         if (messenger['msngr_type'] is not None
#                 and messenger['msngr_username'] is not None):

#             if messenger['msngr_type'] not in ['tm', 'wts']:
#                 raise ValidationError(_(
#                     "Проверьте значение msngr_type: Telegram 'tm', WhatsApp'wts'."))

# def validate_msngr_type_username_full(msngr_type, msngr_username):
#     if msngr_type == 'tm':
#         # Проверка на допустимые символы
#         # (A-z, 0-9, и подчеркивания)
#         if not re.match("^@[A-Za-z0-9_]+$", msngr_username):
#             raise ValidationError(_(
#                 "Недопустимые символы в Telegram username."
#                 " Username должен начинаться с @ и содержать "
#                 "только цифры и буквы."
#             ))

#             # Проверка длины (5-32 символа)
#         if not (5 <= len(msngr_username) <= 32):
#             raise ValidationError(
#                 "Длина Telegram username должна быть"
#                     " от 5 до 32 символов."
#                 )

#     elif msngr_type == 'wts':
#         try:
#             parsed_phone = phonenumbers.parse(msngr_username, None)
#             if not phonenumbers.is_valid_number(parsed_phone):
#                 raise ValidationError(_(
#                     "Неверный формат номера телефона."))
#         except Exception:
#             raise ValidationError(_(
#                         "Неверный формат номера телефона."))


def validate_messenger_account(value):
    if value:
        if 'msngr_username' not in value:
            raise ValidationError(_(
                "Ключа msngr_username нет в передаваемом словаре messenger."))


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
