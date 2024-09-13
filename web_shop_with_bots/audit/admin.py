from django.contrib import admin
from .models import AuditLog
# from .forms import AuditLogForm
from rangefilter.filters import (
    DateRangeQuickSelectListFilter
)
from django.utils.html import format_html


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'status', 'user', 'action', 'ip',
                    'ip_is_routable', 'short_details')
    search_fields = ('user__email', 'user__first_name', 'user__last_name',
                     'action', 'details', 'id', 'ip')
    # form = AuditLogForm
    change_form_template = 'auditlog/change_form.html'
    list_per_page = 10
    list_filter = (('created', DateRangeQuickSelectListFilter),
                   'action', 'status', 'ip_is_routable')

    def short_details(self, obj):
        truncated_value = obj.details[:300] + ('...' if len(obj.details) > 300 else '')
        # Используем div с style чтобы сохранить перенос строк
        return format_html(
            '<div style="white-space: pre-wrap; overflow-wrap: break-word; max-width: 600px;">{}</div>',
            truncated_value
        )
    short_details.short_description = 'Details (short)'
