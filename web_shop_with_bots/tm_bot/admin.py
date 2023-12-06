from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Настройки отображения данных таблицы Message."""
    list_display = ('id', 'profile', 'text', 'created_at')
    list_filter = ('profile',)
