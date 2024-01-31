from django.contrib import admin
from django.utils.html import format_html

from .models import Message, MessengerAccount


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Настройки отображения данных таблицы Message."""
    list_display = ('id', 'profile', 'text', 'created_at')
    list_filter = ('profile',)


@admin.register(MessengerAccount)
class MessagerAccountAdmin(admin.ModelAdmin):
    """Настройки отображения данных таблицы Message."""
    list_display = ('msngr_type', 'msngr_id', 'msngr_username',
                    'get_msngr_link', 'subscription', 'date_joined')
    readonly_fields = ('get_msngr_link',)
    list_filter = ('msngr_type', 'subscription')
    search_fields = ('msngr_id', 'msngr_username')
    # exclude = ('msngr_link',)

    def get_msngr_link(self, instance):
        if instance.msngr_link:
            return format_html(instance.msngr_link)
        return ''
