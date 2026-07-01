from django.utils import translation
from django.urls import reverse
import logging
import traceback
import threading
import re
import html
from django.core.signals import got_request_exception
from audit.models import AuditLog
from django.contrib.contenttypes.models import ContentType
import json
import urllib.parse
from ipware import get_client_ip
from api.utils.utils import _exception_store


logger = logging.getLogger(__name__)

# _exception_store импортируется из utils.py — там custom_exception_handler
# пишет traceback для DRF ошибок (/api/...).
#
# Для Django admin ошибок custom_exception_handler не вызывается,
# поэтому используем сигнал got_request_exception — он срабатывает
# для любых необработанных исключений включая admin.


def _capture_exception_signal(sender, request, **kwargs):
    """
    Ловит ошибки Django admin (и любые другие не-DRF ошибки).
    Для DRF ошибок этот сигнал не срабатывает — там работает
    custom_exception_handler в utils.py.
    Пишем traceback только если он ещё не был записан через
    custom_exception_handler (чтобы не перезаписать).
    """
    if not getattr(_exception_store, 'traceback', None):
        _exception_store.traceback = traceback.format_exc()


got_request_exception.connect(_capture_exception_signal)


class AdminRULocaleMiddleware:
    """ Мидлвэр для отображения админки на русском языке по умолчанию."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
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
        ip, is_routable = get_client_ip(request)

        if request.path.startswith('/api/'):
            if request.body:
                request_body = request.body.decode('utf-8')
            else:
                request_body = '<empty body>'
            logger.info(f"Incoming API request: {ip}({is_routable}) {request.method} {request.path} - Data: {request_body}")
        else:
            logger.info(f"Incoming request: {ip}({is_routable}) {request.method} {request.path} - Data: {request.body}")

        response = self.get_response(request)

        return response


endpoint_skip = [
    # '/admin/',
    '/admin/jsi18n/',
    # '/api/v1/menu/',
    '/__debug__/',    # dubug panel
    '/.well-known/',   # devtools
    '/api/v1/contacts/',
    '/api/v1/promonews/',
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
    '/static/',
]


def _should_skip(path):
    # пропускаем файлы по расширению в любом месте пути
    if re.search(r'\.(jpg|jpeg|png|gif|webp|ico|svg|css|js)(/|$)', path.lower()):
        return True
    for skip_path in endpoint_skip:
        if path.startswith(skip_path):
            return True
    return False


def _get_user_info(request):
    if hasattr(request, 'user') and request.user.is_authenticated:
        return f'User: {request.user.email}', request.user, getattr(request.user, 'base_profile', None)
    return 'Anonymous user', None, None


def _format_body(body):
    """
    Форматирует тело запроса:
    - JSON → красиво с отступами
    - Django формсет (inline редактирование списка) → построчно по формам
    - Обычная form-data → построчно ключ: значение
    """
    if not body:
        return ''

    # Пробуем JSON
    try:
        parsed = json.loads(body)
        return json.dumps(parsed, indent=4, ensure_ascii=False)
    except json.JSONDecodeError:
        pass

    # Пробуем form-data
    params = urllib.parse.parse_qs(body)
    if not params:
        return body

    # Убираем csrf токен — он не нужен в логах
    params.pop('csrfmiddlewaretoken', None)

    # Определяем формсет по наличию TOTAL_FORMS
    total_forms_key = next((k for k in params if k.endswith('-TOTAL_FORMS')), None)
    if total_forms_key:
        prefix = total_forms_key.replace('-TOTAL_FORMS', '')
        total = int(params[total_forms_key][0])

        lines = [f"ФОРМСЕТ '{prefix}', {total} форм:"]
        for i in range(total):
            form_fields = {
                k.replace(f'{prefix}-{i}-', ''): v[0]
                for k, v in params.items()
                if k.startswith(f'{prefix}-{i}-')
            }
            if form_fields:
                fields_str = '  '.join(f"{k}: {v}" for k, v in form_fields.items())
                lines.append(f"  [{i}] {fields_str}")

        # Поля не относящиеся к формсету (кнопки, основные поля формы)
        other = {
            k: v[0] for k, v in params.items()
            if not k.startswith(prefix) and not k.startswith('select_across')
        }
        if other:
            lines.append("Действие: " + '  '.join(f"{k}: {v}" for k, v in other.items()))

        return '\n'.join(lines)

    # Обычная form-data — построчно
    lines = '\n'.join(
        f"  {k}: {', '.join(v)}"
        for k, v in params.items()
    )
    return lines


def _format_get_params(request):
    """Форматирует GET-параметры из URL, например ?city=Beograd&lang=ru"""
    if not request.GET:
        return ''
    lines = '\n'.join(
        f"  {key}: {', '.join(values)}"
        for key, values in request.GET.lists()
    )
    return f"GET ПАРАМЕТРЫ:\n{lines}\n\n"


def _format_response(response):
    if not response.content:
        return ''
    try:
        parsed = json.loads(response.content.decode('utf-8'))
        return json.dumps(parsed, indent=4, ensure_ascii=False)
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass

    raw = response.content.decode('utf-8', errors='replace')

    # Если Django вернул HTML — вытаскиваем только суть
    if raw.strip().startswith('<'):
        title = re.search(r'<title>(.*?)</title>', raw, re.DOTALL)
        exception_value = re.search(
            r'<pre class="exception_value">(.*?)</pre>', raw, re.DOTALL
        )
        parts = []
        if title:
            parts.append(f"Title: {html.unescape(title.group(1).strip())}")
        if exception_value:
            parts.append(
                f"Exception: {html.unescape(exception_value.group(1).strip())}"
            )
        if parts:
            return '\n'.join(parts)
        return f"[HTML response]:\n{raw[:300]}"

    return raw


def _normalize_route(route: str) -> str:
    if not route:
        return route
    route = route.replace('<path:object_id>', '<id>')
    route = route.replace('<int:object_id>', '<id>')
    route = route.replace('<slug:object_id>', '<id>')
    return '/' + route if not route.startswith('/') else route


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            request_body = request.body.decode('utf-8') if request.body else ''
        except Exception:
            request_body = f'[не удалось прочитать тело, content-type: {request.content_type}]'

        ip, is_routable = get_client_ip(request)
        _exception_store.traceback = None

        try:
            response = self.get_response(request)
        except Exception:
            exc_tb = getattr(_exception_store, 'traceback', None) or traceback.format_exc()
            self._log_unhandled_exception(request, request_body, ip, is_routable, exc_tb)
            raise

        # --- endpoint нормализация ---
        match = request.resolver_match
        if match and match.route:
            request._audit_endpoint = _normalize_route(match.route)
        else:
            request._audit_endpoint = request.path

        request._audit_method = request.method
        request._audit_is_admin = request.path.startswith('/admin/')

        # --- фильтры ---
        if _should_skip(request.path):
            return response

        if getattr(request, '_audit_validation_error_logged', False):
            return response

        if response.status_code >= 500:
            exc_tb = getattr(_exception_store, 'traceback', None)
            self._log_error(request, request_body, ip, is_routable, response, exc_tb)

        elif response.status_code >= 400:
            self._log_error(request, request_body, ip, is_routable, response, None)

        elif hasattr(request, '_admin_exception'):
            # 302 редирект после перехваченной ошибки в админке —
            # ошибка была показана пользователю баннером, логируем её
            self._log_admin_handled_error(request, request_body, ip, is_routable)

        elif request._audit_is_admin and request.method == 'GET':
            return response

        elif request._audit_is_admin and request.method == 'POST' and response.status_code == 200:
            # POST в админке вернул 200 — форма не сохранилась (ошибки валидации),
            # но ValidationLoggingMixin уже залогировал через _audit_validation_error_logged
            pass

        else:
            self._log_success(request, request_body, ip, is_routable, response)

        return response

    # --- TARGET ---
    def _extract_target(self, request):
        match = request.resolver_match
        if not match:
            return None, None

        kwargs = match.kwargs or {}
        object_id = (
            kwargs.get('object_id')
            or kwargs.get('pk')
            or kwargs.get('id')
        )

        model = None
        if hasattr(match.func, '__self__'):
            view = match.func.__self__
            if hasattr(view, 'model'):
                model = view.model

        content_type = None
        if model:
            try:
                content_type = ContentType.objects.get_for_model(model)
            except Exception:
                pass

        return object_id, content_type

    # --- SUCCESS ---
    def _log_success(self, request, request_body, ip, is_routable, response):
        try:
            user_info, user, base_profile = _get_user_info(request)
            target_object_id, target_ct = self._extract_target(request)

            AuditLog.objects.create(
                user=user,
                base_profile=base_profile,
                status=response.status_code,
                ip=ip,
                ip_is_routable=is_routable,
                action='Request',
                endpoint=request._audit_endpoint,
                method=request._audit_method,
                is_admin=request._audit_is_admin,
                target_object_id=target_object_id,
                target_content_type=target_ct,
                details=(
                    f"{_format_get_params(request)}"
                    f"ЗАПРОС:\n{_format_body(request_body)}\n\n"
                    f"ОТВЕТ:\n{_format_response(response)}\n"
                )
            )
        except Exception as log_exc:
            logger.error(f"AuditMiddleware._log_success error: {log_exc}")

    # --- ERROR ---
    def _log_error(self, request, request_body, ip, is_routable, response, exc_tb=None):
        try:
            user_info, user, base_profile = _get_user_info(request)
            response_body = _format_response(response)
            target_object_id, target_ct = self._extract_target(request)

            traceback_section = ''
            if exc_tb:
                traceback_section = f"TRACEBACK:\n{exc_tb}\n\n"

            AuditLog.objects.create(
                user=user,
                base_profile=base_profile,
                action='Error',
                status=response.status_code,
                ip=ip,
                ip_is_routable=is_routable,
                endpoint=request._audit_endpoint,
                method=request._audit_method,
                is_admin=request._audit_is_admin,
                target_object_id=target_object_id,
                target_content_type=target_ct,
                details=(
                    f"{traceback_section}"
                    f"{_format_get_params(request)}"
                    f"ОТВЕТ СЕРВЕРА:\n{response_body}\n\n"
                    f"ЗАПРОС:\n{_format_body(request_body)}\n"
                )
            )
        except Exception as log_exc:
            logger.error(f"AuditMiddleware._log_error error: {log_exc}")

    # --- ADMIN HANDLED ERROR ---
    def _log_admin_handled_error(self, request, request_body, ip, is_routable):
        """
        Логирует ошибки которые были перехвачены в админке через _handle_exception
        и показаны пользователю баннером. Django вернул 302, но это была ошибка.
        """
        try:
            user_info, user, base_profile = _get_user_info(request)
            target_object_id, target_ct = self._extract_target(request)

            exc_tb = getattr(request, '_admin_exception', '')
            exc_msg = getattr(request, '_admin_exception_msg', '')

            AuditLog.objects.create(
                user=user,
                base_profile=base_profile,
                action='Error',
                status=500,
                ip=ip,
                ip_is_routable=is_routable,
                endpoint=request._audit_endpoint,
                method=request._audit_method,
                is_admin=True,
                target_object_id=target_object_id,
                target_content_type=target_ct,
                details=(
                    f"ОШИБКА: {exc_msg}\n\n"
                    f"TRACEBACK:\n{exc_tb}\n\n"
                    f"{_format_get_params(request)}"
                    f"ЗАПРОС:\n{_format_body(request_body)}\n"
                )
            )
        except Exception as log_exc:
            logger.error(f"AuditMiddleware._log_admin_handled_error error: {log_exc}")

    # --- UNHANDLED EXCEPTION ---
    def _log_unhandled_exception(self, request, request_body, ip, is_routable, exc_tb):
        try:
            user_info, user, base_profile = _get_user_info(request)
            target_object_id, target_ct = self._extract_target(request)

            AuditLog.objects.create(
                user=user,
                base_profile=base_profile,
                action='Error',
                status=500,
                ip=ip,
                ip_is_routable=is_routable,
                endpoint=request.path,
                method=request.method,
                is_admin=request.path.startswith('/admin/'),
                target_object_id=target_object_id,
                target_content_type=target_ct,
                details=(
                    f"{_format_get_params(request)}"
                    f"ЗАПРОС:\n{_format_body(request_body)}\n\n"
                    f"TRACEBACK:\n{exc_tb}\n"
                )
            )
        except Exception as log_exc:
            logger.error(f"AuditMiddleware._log_unhandled_exception error: {log_exc}")
