"""
Миксин для логирования ошибок валидации форм в AuditLog
и показа баннера об ошибке вместо белого экрана 500.

Использование:
    from utils.admin_audit_mixin import ValidationLoggingMixin

    @admin.register(Dish)
    class DishAdmin(ValidationLoggingMixin, TranslatableAdmin):
        ...

    @admin.register(Order)
    class OrderAdmin(ValidationLoggingMixin, admin.ModelAdmin):
        ...
"""
import logging
import traceback
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from ipware import get_client_ip
from audit.models import AuditLog

logger = logging.getLogger(__name__)


def _normalize_endpoint(request):
    """
    Возвращает нормализованный endpoint без конкретных id.
    /admin/shop/order/34152/change/ → /admin/shop/order/<id>/change/
    Используем resolver_match если доступен, иначе request.path.
    """
    match = getattr(request, 'resolver_match', None)
    if match and match.route:
        route = match.route
        route = route.replace('<path:object_id>', '<id>')
        route = route.replace('<int:object_id>', '<id>')
        route = route.replace('<slug:object_id>', '<id>')
        return '/' + route if not route.startswith('/') else route
    return request.path


class ValidationLoggingMixin:
    """
    Подключается к любому ModelAdmin. Делает две вещи:

    1. Перехватывает необработанные исключения (500) в changelist_view,
       change_view и add_view — показывает красный баннер с текстом ошибки
       вместо белого экрана, пользователь остаётся на форме.
       Сохраняет исключение в request._admin_exception чтобы middleware
       мог записать его в журнал.

    2. Перехватывает POST где форма не прошла валидацию
       — пишет все ошибки валидации в AuditLog.
    """

    # ------------------------------------------------------------------
    # 1. Защита от белого экрана 500
    # ------------------------------------------------------------------

    def _handle_exception(self, request, exc, object_id=None):
        """Показывает баннер с ошибкой и редиректит обратно на форму.
        Сохраняет traceback в request для middleware."""
        exc_text = traceback.format_exc()

        # Сохраняем в request — middleware прочитает и запишет в журнал
        request._admin_exception = exc_text
        request._admin_exception_msg = f"{type(exc).__name__}: {exc}"

        messages.error(
            request,
            f"Ошибка: {type(exc).__name__}: {exc}"
        )
        # Сохраняем GET параметры (фильтры) при редиректе
        redirect_url = request.get_full_path()
        return HttpResponseRedirect(redirect_url)

    def changelist_view(self, request, extra_context=None):
        try:
            return super().changelist_view(request, extra_context)
        except Exception as e:
            return self._handle_exception(request, e)

    def add_view(self, request, form_url='', extra_context=None):
        try:
            return super().add_view(request, form_url, extra_context)
        except Exception as e:
            return self._handle_exception(request, e)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        try:
            return super().change_view(request, object_id, form_url, extra_context)
        except Exception as e:
            return self._handle_exception(request, e, object_id)

    # ------------------------------------------------------------------
    # 2. Логирование ошибок валидации формы
    # ------------------------------------------------------------------

    def _changeform_view(self, request, object_id, form_url, extra_context):
        response = super()._changeform_view(
            request, object_id, form_url, extra_context
        )

        # Нас интересуют только POST, где форма не сохранилась.
        if request.method != 'POST':
            return response

        # При успешном сохранении — redirect без context_data.
        if not hasattr(response, 'context_data'):
            return response

        adminform = response.context_data.get('adminform')
        if not adminform:
            return response

        form = adminform.form

        # Собираем ошибки основной формы
        form_errors = {}
        for field, errors in form.errors.items():
            field_label = field
            if field != '__all__' and field in form.fields:
                field_label = form.fields[field].label or field
            form_errors[field_label] = [str(e) for e in errors]

        # Собираем ошибки инлайнов
        inline_errors = {}
        has_inline_errors = False

        for inline_formset in response.context_data.get('inline_admin_formsets', []):
            formset = inline_formset.formset
            inline_name = str(inline_formset.opts.verbose_name)

            if formset.non_form_errors():
                has_inline_errors = True
                inline_errors[f"{inline_name} [общие]"] = {
                    '__all__': [str(e) for e in formset.non_form_errors()]
                }

            for i, inline_form in enumerate(formset.forms):
                if not inline_form.errors:
                    continue

                has_inline_errors = True
                key = f"{inline_name} [{i}]"
                inline_errors[key] = {}

                for field, errors in inline_form.errors.items():
                    field_label = field
                    if field != '__all__' and field in inline_form.fields:
                        field_label = inline_form.fields[field].label or field
                    inline_errors[key][field_label] = [str(e) for e in errors]

        if not form_errors and not has_inline_errors:
            return response

        # Формируем details
        lines = ["ОШИБКА ВАЛИДАЦИИ ФОРМЫ", ""]

        if form_errors:
            lines.append("ОШИБКИ ФОРМЫ:")
            for field, errors in form_errors.items():
                lines.append(f"  {field}: {', '.join(errors)}")

        if inline_errors:
            lines.append("ОШИБКИ ИНЛАЙНОВ:")
            for section, errors in inline_errors.items():
                lines.append(f"  {section}:")
                for field, errs in errors.items():
                    lines.append(f"    {field}: {', '.join(errs)}")

        try:
            ip, is_routable = get_client_ip(request)
            user = request.user if request.user.is_authenticated else None
            base_profile = getattr(user, 'base_profile', None) if user else None
            target_ct = ContentType.objects.get_for_model(self.model)

            # Флаг для middleware — чтобы не было дублирующей записи
            request._audit_validation_error_logged = True

            AuditLog.objects.create(
                user=user,
                base_profile=base_profile,
                action='Error',           # единый тип для всех ошибок
                status=200,
                ip=ip,
                ip_is_routable=is_routable,
                endpoint=_normalize_endpoint(request),  # без конкретного id
                method=request.method,
                is_admin=True,
                target_content_type=target_ct,
                target_object_id=str(object_id) if object_id else None,
                details='\n'.join(lines),
            )
        except Exception as e:
            logger.error(f"ValidationLoggingMixin: ошибка записи в AuditLog: {e}")

        return response
