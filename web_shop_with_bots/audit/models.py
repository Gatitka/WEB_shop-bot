from django.db import models
from django.contrib.auth import get_user_model
from users.models import BaseProfile


User = get_user_model()


class AuditLog(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL,
                             null=True, blank=True)
    base_profile = models.ForeignKey(BaseProfile,
                                     on_delete=models.SET_NULL,
                                     null=True, blank=True)
    status = models.CharField(max_length=3, null=True, blank=True)
    action = models.CharField(max_length=255)
    details = models.TextField()
    ip = models.GenericIPAddressField(blank=True, null=True)
    ip_is_routable = models.BooleanField(blank=True, null=True)

    def short_details(self):
        return self.details[:300] + ('...' if len(self.details) > 300 else '')
    short_details.short_description = 'Details (short)'

    def __str__(self):
        return f'{self.created} - {self.action} by {self.user}'

    class Meta:
        verbose_name = 'Активность пользователей'
        verbose_name_plural = 'Активности пользователей'
        ordering = ('-created',)
