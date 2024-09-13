from django.utils import translation
from django.urls import reverse
import logging
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now
from audit.models import AuditLog
import json
import urllib.parse
from ipware import get_client_ip


logger = logging.getLogger(__name__)


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
                and not request.path.startswith('/api/v1/auth/')):

            translation.activate('en')
            request.LANGUAGE_CODE = 'en'
        else:
            translation.activate(request.LANGUAGE_CODE)

        response = self.get_response(request)

        return response


class APILoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request path starts with '/api/'
        ip, is_routable = get_client_ip(request)

        if request.path.startswith('/api/'):
            if request.body:
                request_body = request.body.decode('utf-8')
            else:
                request_body = '<empty body>'
            logger.info(f"Incoming API request: {ip}({is_routable}) {request.method} {request.path} - Data: {request_body}")

        else:
            logger.info(f"Incoming request: {ip}({is_routable}) {request.method} {request.path} - Data: {request.body}")

        # Get the response
        response = self.get_response(request)

        return response


endpoint_skip = [
    '/admin/',
    '/api/v1/promonews/',
    '/api/v1/contacts/',
    '/api/v1/menu/',
    '/api/v1/shopping_cart/',
    '/api/v1/get_dish_price/',
    '/api/v1/get_user_data/',
    '/api/v1/get_discounts/',
    '/api/v1/get_google_api_key/',
    '/api/v1/calculate_delivery/',
    '/api/v1/auth/jwt/refresh/',
    '/summernote/',
    '/redoc/',
    '/media/',
    '/static/',]

tasks = {
    "/api/v1/me/my_addresses/": "Обращение к моим адресам",
    "/api/v1/me/my_orders/": "Обращение к моим заказам",
    "/api/v1/create_order_takeaway/": "Сохранение заказа самовывоз",
    "/api/v1/create_order_delivery/": "Сохранение заказа доставка",
    "/api/v1/create_order_takeaway/pre_checkout/":
                    "Предварительный рассчет заказа самовывоз",
    "/api/v1/create_order_delivery/pre_checkout/":
                    "Предварительный рассчет заказа доставка",

    "/api/v1/auth/jwt/refresh/": "Обновление токена доступа",
    "/api/v1/auth/jwt/create/": "Логин в личный кабинет",
    "/api/v1/auth/users/me/":
                    "Личные данные/мессенджер просмотр, редакция, удаление",

    "/api/v1/save_bot_order/":
                    "Сохранение заказа из ТМ Бота / обновление статуса заказа",
}

methods = {
    'GET': 'ЧТЕН',
    'POST': 'СОЗД/ИЗМЕН',
    'PUT': 'ИЗМЕН',
    'PATCH': 'ИЗМЕН',
    'DELETE': 'УДАЛ',
}


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_body = request.body.decode('utf-8') if request.body else ''
        response = None
        try:
            response = self.process_request(request, request_body)
        except Exception as e:
            response = self.get_response(request)
            self.process_exception(request,
                                   response.content.decode('utf-8'),
                                   request_body,
                                   response.status_code)

        finally:
            if response is not None:
                return response
            else:
                return self.get_response(request)

    def process_request(self, request, request_body):
        response = self.get_response(request)

        exception_flag = getattr(response, 'exception', False)
        ip, is_routable = get_client_ip(request)

        if exception_flag is False and response.status_code != 500:
            # Проверяем, нужно ли логировать
            logging_needed = True
            for path in endpoint_skip:
                if request.path.startswith(path):
                    logging_needed = False
                    break

            if logging_needed:
                user_info = 'Anonymous user'
                user = None
                base_profile = None
                if hasattr(request, 'user') and request.user.is_authenticated:
                    user_info = f'User: {request.user.email}'
                    user = request.user
                    base_profile = user.base_profile

                formatted_request = ''
                if request_body:
                    try:
                        request_json = json.loads(request_body)
                        formatted_request = json.dumps(request_json,
                                                       indent=4,
                                                       ensure_ascii=False)
                    except json.JSONDecodeError:
                        formatted_request = urllib.parse.parse_qs(
                            request_body)

                formatted_response = ''
                if response.content:
                    try:
                        response_json = json.loads(response.content.decode(
                                                                    'utf-8'))
                        formatted_response = json.dumps(response_json,
                                                        indent=4,
                                                        ensure_ascii=False)
                    except json.JSONDecodeError:
                        formatted_response = response.content.decode('utf-8')

                task = tasks.get(request.path, "Задача не описана")
                method = methods.get(request.method, "")

                log_entry = AuditLog(user=user,
                                     base_profile=base_profile,
                                     status=response.status_code,
                                     ip=ip,
                                     ip_is_routable=is_routable,
                                     action='Request',
                                     details=(
                                         f"{user_info} УСПЕШНЫЙ ЗАПРОС\n"
                                         f"{task}   метод: {method}\n"
                                         f"эндпоинт: {request.path}\n\n"
                                         f"ЗАПРОС: {formatted_request}\n"
                                         f"ОТВЕТ: {formatted_response}\n\n"
                                     )
                                     )
                log_entry.save()
                return response
        elif response.status_code != 500:
            self.process_exception(request,
                                   response.content.decode('utf-8'),
                                   request_body,
                                   response.status_code)
            return response

        else:
            self.process_exception(request,
                                   response.content.decode('utf-8'),
                                   request_body,
                                   500)
            raise Exception
        return response

    def process_exception(self, request, exception, request_body='', status_code=500):
        ip, is_routable = get_client_ip(request)
        try:
            user_info = 'Anonymous user'
            user = None
            base_profile = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_info = f'User: {request.user.email}'
                user = request.user
                base_profile = user.base_profile

            formatted_request = ''
            if request_body:
                try:
                    request_json = json.loads(request_body)
                    formatted_request = json.dumps(request_json, indent=4,
                                                   ensure_ascii=False)
                except json.JSONDecodeError:
                    formatted_request = request_body

            task = tasks.get(request.path, "Задача не описана")
            method = methods.get(request.method, "")

            log_entry = AuditLog(user=user,
                                 base_profile=base_profile,
                                 action='Error',
                                 status=status_code,
                                 ip=ip,
                                 ip_is_routable=is_routable,
                                 details=(
                                     f"{user_info} ОШИБКА ЗАПРОСА\n"
                                     f"{task}   метод: {method}\n"
                                     f"адрес: {request.path}\n\n"
                                     f"ОШИБКА: {str(exception)}\n\n"
                                     f"ЗАПРОС: {formatted_request}\n"
                                 )
                                 )
            log_entry.save()
        except Exception as log_exception:
            # Handle any errors that occur during logging to avoid masking the original exception
            logger.error(f"Error logging exception: {log_exception}")
            logger.error(f"Original exception: {exception}")
