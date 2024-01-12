from django.db import models
from django.utils.safestring import mark_safe


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
    title_en = models.CharField(
        max_length=100,
        verbose_name='заголовок en',
        blank=True, null=True
    )
    full_text_en = models.TextField(
        max_length=600,
        verbose_name='описание en',
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
    image_rus = models.ImageField(
        upload_to='promo/',
        null=True,
        default=None,
        blank=True,
        verbose_name='Изображение',
        )
    image_en = models.ImageField(
        upload_to='promo/',
        null=True,
        default=None,
        blank=True,
        verbose_name='Изображение',
        )
    image_srb = models.ImageField(
        upload_to='promo/',
        null=True,
        default=None,
        blank=True,
        verbose_name='Изображение',
        )

    def admin_photo_rus(self):
        if self.image_rus:
            return mark_safe(
                '<img src="{}" width="100" />'.format(self.image_rus.url)
                )
        missing_image_url = "icons/missing_image.jpg"
        return mark_safe(
            '<img src="{}" width="100" />'.format(missing_image_url)
            )

    def admin_photo_srb(self):
        if self.image_srb:
            return mark_safe(
                '<img src="{}" width="100" />'.format(self.image_srb.url)
                )
        missing_image_url = "icons/missing_image.jpg"
        return mark_safe(
            '<img src="{}" width="100" />'.format(missing_image_url)
            )

    def admin_photo_en(self):
        if self.image_en:
            return mark_safe(
                '<img src="{}" width="100" />'.format(self.image_en.url)
                )
        missing_image_url = "icons/missing_image.jpg"
        return mark_safe(
            '<img src="{}" width="100" />'.format(missing_image_url)
            )

    admin_photo_rus.short_description = 'Image_rus'
    admin_photo_rus.allow_tags = True
    admin_photo_srb.short_description = 'Image_srb'
    admin_photo_srb.allow_tags = True
    admin_photo_en.short_description = 'Image_EN'
    admin_photo_en.allow_tags = True

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
