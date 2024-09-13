from django import forms
from .models import AuditLog
from django.utils.html import format_html


# class ShortTextWidget(forms.Widget):
#     def render(self, name, value, attrs=None, renderer=None):
#         if not value:
#             return ''
#         truncated_value = obj.details[:300] + ('...' if len(obj.details) > 300 else '')
#         return format_html('<div style="white-space: pre-wrap; overflow-wrap: break-word; width: 100%;">{}</div>', truncated_value)


# class AuditLogForm(forms.ModelForm):
#     class Meta:
#         model = AuditLog
#         fields = '__all__'
#         widgets = {
#             'details': ShortTextWidget,
#         }
