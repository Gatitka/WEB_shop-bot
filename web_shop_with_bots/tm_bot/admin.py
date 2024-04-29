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
    readonly_fields = ('get_msngr_link', 'date_joined')
    list_filter = ('msngr_type', 'subscription')
    search_fields = ('msngr_id', 'msngr_username')
    fieldsets = (
        ('Основное', {
            'fields': (
                ('msngr_type', 'language', 'date_joined'),
                ('msngr_username', 'get_msngr_link'),
                ('notes'),
                ('subscription'),
            )
        }),
        ('Дополнительно', {
            'fields': (
                ('msngr_phone'),
                ('msngr_link'),
                ('msngr_id',),
                ('tm_chat_id'),

            )
        })
    )

    def get_msngr_link(self, instance):
        if instance.msngr_link:
            return format_html(instance.msngr_link)
        return ''
    get_msngr_link.short_description = 'Перейти в чат'
