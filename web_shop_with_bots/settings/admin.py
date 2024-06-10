from django.contrib import admin
from settings.models import OnlineSettings
from django.http import HttpResponseRedirect
from django.urls import reverse
from utils.utils import activ_actions


@admin.register(OnlineSettings)
class SettingsAdmin(admin.ModelAdmin):
    """Настройки сайта."""

    def changelist_view(self, request, extra_context=None):
        obj = OnlineSettings.objects.first()
        if obj:
            return HttpResponseRedirect(
                reverse('admin:settings_onlinesettings_change',
                        args=[obj.pk]))

        return super().changelist_view(request, extra_context)
