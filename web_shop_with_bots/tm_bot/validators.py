import re

import phonenumbers
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import hashlib
import hmac
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_msgr_data_validated(data):
    # Проверяем, что оба поля заполнены
    msngr_type = data.get('msngr_type')
    if not msngr_type:
        raise ValidationError(
            "Field 'msngr_type' must be filled.")

    validate_msngr_type(msngr_type)

    if msngr_type == 'tm':
        # Телеграм → должны быть id, hash, auth_date
        # USERNAME может не быть изначально!!!!!!
        required = ("msngr_id", "auth_date", "hash")
        missing = []
        for f in required:
            if f == "msngr_id" and f not in data:
                missing.append('id')
            elif f not in data:
                missing.append(f)
        if missing:
            raise ValidationError(
                {f"Missing Telegram fields: {', '.join(missing)}"}
            )

    elif msngr_type == 'wts':
        phone = data.get('msngr_username')
        # WhatsApp → нужен тип wts и телефон
        try:
            parsed_phone = phonenumbers.parse(phone, None)
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
        value = value.strip()
        if value.startswith('+'):
            # Проверка на допустимые символы WhatsApp
            try:
                parsed_phone = phonenumbers.parse(value, None)
                if not phonenumbers.is_valid_number(parsed_phone):
                    raise ValidationError(_(
                        "Wts username must start with '+' or invalid phone number."))
                msngr_type = 'wts'
            except Exception:
                raise ValidationError(_(
                            "Wts username must start with '+' or invalid phone number."))

        # Всё остальное считаем Telegram username
        # Telegram username
        username = value[1:] if value.startswith('@') else value

        # Проверка длины
        if not (5 <= len(username) <= 32):
            raise ValidationError(_("Telegram username length from 5 to 32 symbols."))

        # # Проверка допустимых символов и формы
        # # начинается с буквы, потом буквы/цифры/подчёркивания, не заканчивается на '_'
        # pattern = r"^[A-Za-z][A-Za-z0-9_]*[A-Za-z0-9]$"
        # if not re.fullmatch(pattern, username):
        #     raise ValidationError(_(
        #         "Недопустимый Telegram username. "
        #         "Допустимы латинские буквы, цифры и подчёркивания, "
        #         "должен начинаться с буквы и не заканчиваться на '_'."
        #     ))


def check_telegram_auth(data: dict, bot_token: str) -> bool:
    """
    Проверка авторизации через Telegram Widget Login
    (привязка аккаунта в профиле)
    """

    if not data.get('hash'):
        return True

    # Какие поля не входят в подпись
    NONTELEGRAM_FIELDS = {"city", "msngr_type", "is_bot"}

    # Безопасно извлекаем поля, НО:
    # если фронт прислал "", мы НЕ должны добавлять их,
    # потому что Telegram не добавляет пустые поля в подпись.
    def _pop_clean(src, key, new_key):
        val = src.pop(key, None)
        if val is not None and val != "":
            data[new_key] = val

    # переносим только непустые
    _pop_clean(data, "msngr_id", "id")
    _pop_clean(data, "msngr_first_name", "first_name")
    _pop_clean(data, "msngr_last_name", "last_name")
    _pop_clean(data, "msngr_username", "username")

    # удаляем тип мессенджера — не участвует в подписи
    data.pop("msngr_type", None)


    # 1. Извлекаем hash
    logger.debug("\n------->Data from bot:\n %s.\nBot_token: %s\n# 1. Извлекаем hash.",
                 data, bot_token[-10:])
    received_hash = data.pop("hash", None)
    if received_hash is None:
        logger.debug("Received HASH is none.")
        return False
    logger.debug("Received_hash: ****%s", received_hash[-10:])
    # 2. Фильтруем только разрешённые поля

    filtered_data = {k: v for k, v in data.items() if k not in NONTELEGRAM_FIELDS}
    # filtered_data = data
    logger.debug("\n2. Фильтруем только разрешённые поля.\n"
                 "Filtered_data: %s", filtered_data)
    # 3. Формируем строку для проверки
    data_check_arr = []
    for key in sorted(filtered_data.keys()):
        value = filtered_data[key]
        data_check_arr.append(f"{key}={value}")
    data_check_string = "\n".join(data_check_arr)
    logger.debug("3. Формируем строку для проверки.\n"
                 "Data_check_string: %s", data_check_string)

    # 4. Секретный ключ = SHA256(bot_token)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    logger.debug("Секретный ключ = SHA256(bot_token).")

    # 5. Считаем HMAC
    hmac_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    logger.debug("5. Считаем HMAC.\n"
                 "hmac_hash:%s", hmac_hash)

    validated = hmac_hash == received_hash
    # 6. Сравниваем
    logger.debug("6. Сравниваем. Результат: %s", validated)
    return validated
