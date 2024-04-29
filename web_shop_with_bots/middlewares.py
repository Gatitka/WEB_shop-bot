from django.utils import translation
from django.urls import reverse
from django.http import HttpResponseRedirect


class AdminRULocaleMiddleware:
    """ Мидлвэр для отображения админки на русском языке по умолчанию."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Если запрос идет на административную панель
        if request.path.startswith(reverse('admin:index')):
            translation.activate('ru')
            request.LANGUAGE_CODE = 'ru'
        else:
            translation.activate(request.LANGUAGE_CODE)

        response = self.get_response(request)

        return response


class APIENLocaleMiddleware:
    """Мидлвэр для установки языка 'en' для запросов начинающихся с 'api/'."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Если запрос идет на апи
        if (request.path.startswith('/api/')
                and not request.path.startswith('/api/v1/auth/users/')):

            translation.activate('en')
            request.LANGUAGE_CODE = 'en'
        else:
            translation.activate(request.LANGUAGE_CODE)

        response = self.get_response(request)

        return response
