from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response
from django.db import IntegrityError
import re

import logging

# Создаем логгер
logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    # Проверяем, есть ли атрибут detail в исключении
    # Получаем сообщение об ошибке
    error_message = str(exc)

    # Логируем сообщение об ошибке
    logger.error(error_message, exc_info=True)

    if hasattr(exc, "detail"):
        # Если DEBUG = False, не возвращаем трейсбеки
        if not settings.DEBUG:
            return Response({"message": "Internal Server Error"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Если у нас словарь в detail, возвращаем его содержимое
        if isinstance(exc.detail, dict):
            return Response({"message": exc.detail},
                            status=status.HTTP_400_BAD_REQUEST)

        # Если у нас объект ErrorDetail, возвращаем его строковое представление
        elif isinstance(exc.detail, ErrorDetail):
            return Response({"message": str(exc.detail)},
                            status=status.HTTP_400_BAD_REQUEST)

        # Если у нас список в detail, возвращаем строки всех элементов списка
        elif isinstance(exc.detail, list):
            error_messages = [str(detail) for detail in exc.detail]
            return Response({"message": error_messages},
                            status=status.HTTP_400_BAD_REQUEST)

    elif isinstance(exc, IntegrityError):
            parts = error_message.split('Ключ ')
            if len(parts) > 1:
                # Извлекаем вторую часть (после 'Ключ "')
                part = parts[1]
                # Находим индекс закрывающей скобки ")"
                closing_bracket_index = part.find(")")
                if closing_bracket_index != -1:
                    # Извлекаем часть строки с названием поля
                    key = part[2:closing_bracket_index]
                    # Возвращаем сообщение об ошибке с указанием поля
                    return Response({"message": {key: ["Already exists."]}}, status=status.HTTP_400_BAD_REQUEST)

    # Если detail отсутствует, возвращаем общее сообщение об ошибке
    if not settings.DEBUG:
        return Response({"message": "Internal Server Error"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)





if __name__ == '__main__':
    pass
