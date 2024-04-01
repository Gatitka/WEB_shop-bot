from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    # Проверяем, есть ли атрибут detail в исключении
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

    # Если detail отсутствует, возвращаем общее сообщение об ошибке
    if not settings.DEBUG:
        return Response({"message": "Internal Server Error"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


if __name__ == '__main__':
    pass
