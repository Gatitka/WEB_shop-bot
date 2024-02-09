from django.db import models
from django.utils.safestring import mark_safe
from parler.models import TranslatableModel, TranslatedFields


class PromoNews(TranslatableModel):
    """ Модель для промо новостей."""
    translations = TranslatedFields(
        title=models.CharField(
            max_length=100,
            verbose_name='заголовок',
            blank=True, null=True
        ),
        full_text=models.TextField(
            max_length=600,
            verbose_name='описание',
            blank=True, null=True
        ),
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
    image_ru = models.ImageField(
            upload_to='promo/',
            verbose_name='изображение ru',
            blank=True, null=True
    )
    image_en = models.ImageField(
            upload_to='promo/',
            verbose_name='изображение en',
            blank=True, null=True
    )
    image_sr = models.ImageField(
            upload_to='promo/',
            verbose_name='изображение sr',
            blank=True, null=True
    )

    def admin_image_ru(self):
        if self.image_ru:
            return mark_safe(
                '<img src="{}" width="100" />'.format(self.image_ru.url)
                )
        missing_image_url = "icons/missing_image.jpg"
        return mark_safe(
            '<img src="{}" width="100" />'.format(missing_image_url)
            )

    def admin_image_en(self):
        if self.image_en:
            return mark_safe(
                '<img src="{}" width="100" />'.format(self.image_en.url)
                )
        missing_image_url = "icons/missing_image.jpg"
        return mark_safe(
            '<img src="{}" width="100" />'.format(missing_image_url)
            )

    def admin_image_sr(self):
        if self.image_sr:
            return mark_safe(
                '<img src="{}" width="100" />'.format(self.image_sr.url)
                )
        missing_image_url = "icons/missing_image.jpg"
        return mark_safe(
            '<img src="{}" width="100" />'.format(missing_image_url)
            )

    class Meta:
        ordering = ['-created']
        verbose_name = 'промо-новость'
        verbose_name_plural = 'промо-новости'

    def __str__(self):
        # Use the `safe_translation_getter` to retrieve the translated title
        title = self.safe_translation_getter('title', language_code='ru')
        return title or f'PromoNews #{self.pk}'


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
