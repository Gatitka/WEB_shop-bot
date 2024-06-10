from django.db import models


# Create your models here.
class OnlineSettings(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name='название'
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='активен'
    )
    open_time = models.TimeField(
        'открытие',
        blank=True, null=True
    )
    close_time = models.TimeField(
        'закрытие',
        blank=True, null=True
    )

    class Meta:
        verbose_name = 'Настройки'
        verbose_name_plural = 'Настройки'

    def __str__(self):
        return self.name
