from django.contrib import admin
from .models import AuditLog
# from .forms import AuditLogForm
from rangefilter.filters import (
    DateTimeRangeFilter
)
from django.utils.html import format_html


from django.contrib.contenttypes.models import ContentType
from django.contrib.admin import SimpleListFilter


class ContentTypeFilter(admin.SimpleListFilter):
    title = 'Тип объекта'
    parameter_name = 'target_content_type'

    def lookups(self, request, model_admin):
        # Один запрос — JOIN через select_related
        cts = (ContentType.objects
               .filter(audit_logs__isnull=False)
               .distinct())
        return [(ct.id, str(ct)) for ct in cts]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(target_content_type_id=self.value())
        return queryset


class ActionFilter(SimpleListFilter):
    title = 'Action'
    parameter_name = 'action'

    def lookups(self, request, model_admin):
        # фиксированные значения — без запроса к БД
        return [('Request', 'Request'), ('Error', 'Error')]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(action=self.value())
        return queryset


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    def custom_endpoint(self, obj):
        return format_html('<span>{}<br>{}   {}</span>',
                            obj.endpoint,
                            obj.method,
                            obj.action)
    custom_endpoint.short_description = 'REQUEST'

    def custom_user(self, obj):
        return format_html('<span>{}<br>{}</span>',
                            obj.user,
                            obj.ip)
    custom_user.short_description = 'USER'

    list_display = ('id', 'created', 'status', 'custom_endpoint', 'custom_user',
                    'short_details')
    readonly_fields = ['custom_endpoint', 'custom_user']
    search_fields = ('user__email', 'user__first_name', 'user__last_name',
                     'details', 'ip', 'endpoint', 'target_object_id')
    # form = AuditLogForm
    change_form_template = 'auditlog/change_form.html'
    list_per_page = 15
    list_filter = (('created', DateTimeRangeFilter),
                   ActionFilter, 'status', 'ip_is_routable',
                   'method', 'endpoint', 'is_admin',
                   ContentTypeFilter)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'base_profile', 'target_content_type'
        )

    def short_details(self, obj):
        truncated_value = obj.details[:300] + ('...' if len(obj.details) > 300 else '')
        # Используем div с style чтобы сохранить перенос строк
        return format_html(
            '<div style="white-space: pre-wrap; overflow-wrap: break-word; max-width: 600px;">{}</div>',
            truncated_value
        )
    short_details.short_description = 'Details (short)'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
