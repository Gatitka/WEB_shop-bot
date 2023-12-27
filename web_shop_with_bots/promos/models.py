from django.db import models


class PromoNews(models.Model):
    """ Модель для промо новостей."""
    title_rus = models.CharField(
        max_length=100,
        verbose_name='заголовок рус'
    )
    full_text_rus = models.TextField(
        max_length=600,
        verbose_name='описание рус'
    )
    title_eng = models.CharField(
        max_length=100,
        verbose_name='заголовок eng',
        blank=True, null=True
    )
    full_text_eng = models.TextField(
        max_length=600,
        verbose_name='описание eng',
        blank=True, null=True
    )
    title_srb = models.CharField(
        max_length=100,
        verbose_name='заголовок srb',
        blank=True, null=True
    )
    full_text_srb = models.TextField(
        max_length=600,
        verbose_name='описание srb',
        blank=True, null=True
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='активен'
    )
    city = models.CharField(
        max_length=50,
        verbose_name='город',
        blank=True,
        null=True
    )
    created = models.DateField(
        'Дата добавления', auto_now_add=True
    )
    # image

    class Meta:
        ordering = ['-created']
        verbose_name = 'промо-новость'
        verbose_name_plural = 'промо-новости'

    def __str__(self):
        return f'{self.title_rus}'


class Promocode(models.Model):
    """ Модель для промокодов."""
    title_rus = models.CharField(
        max_length=100,
        verbose_name='заголовок рус'
    )
    promocode = models.CharField(
        max_length=6,
        verbose_name='код'
    )
    discount = models.CharField(
        max_length=5,
        verbose_name='скидка'
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='активен'
    )
    created = models.DateField(
        'Дата добавления', auto_now_add=True
    )
    valid_from = models.DateTimeField(
        'Начало действия'
    )
    valid_to = models.DateTimeField(
        'Окончание действия'
    )

    class Meta:
        ordering = ['-created']
        verbose_name = 'промокод'
        verbose_name_plural = 'промокоды'

    def __str__(self):
        return f'{self.title_rus}'

    @classmethod
    def is_valid(cls, promocode):
        return Promocode.objects.filter(promocode=promocode).exists()
