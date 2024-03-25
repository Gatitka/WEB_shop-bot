from django.db import models
from django.utils.safestring import mark_safe
from parler.models import TranslatableModel, TranslatedFields
from django.conf import settings
from django.utils import timezone
from users.models import BaseProfile
from .services import get_promocode_discount_amount


class PromoNews(TranslatableModel):
    """ Модель для промо новостей."""
    translations = TranslatedFields(
        title=models.TextField(
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
        max_length=20,
        verbose_name="город",
        choices=settings.CITY_CHOICES
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
    image_sr_latn = models.ImageField(
            upload_to='promo/',
            verbose_name='изображение sr-latn',
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

    def admin_image_sr_latn(self):
        if self.image_sr_latn:
            return mark_safe(
                '<img src="{}" width="100" />'.format(self.image_sr_latn.url)
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


class Promocode(TranslatableModel):
    """ Модель для промокодов."""
    translations = TranslatedFields(
        description=models.CharField(
            max_length=100,
            verbose_name='описание',
            blank=True, null=True
        )
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='Активен'
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

    title_rus = models.CharField(
        max_length=100,
        verbose_name='заголовок рус'
    )
    code = models.CharField(
        max_length=8,
        verbose_name='код',
        unique=True
    )
    ttl_am_discount_percent = models.DecimalField(
        verbose_name='Скидка на весь заказ, %',
        help_text="Внесите скидку, прим. для 10% внесите '10,00'.",
        max_digits=7, decimal_places=2,
        null=True,
        blank=True,
    )
    ttl_am_discount_amount = models.DecimalField(
        verbose_name='Скидка на весь заказ, DIN',
        help_text="Внесите скидку, прим. '300,00'.",
        max_digits=7, decimal_places=2,
        null=True,
        blank=True,
    )
    free_delivery = models.BooleanField(
        default=False,
        verbose_name='Бесплатная доставка'
    )
    gift = models.BooleanField(
        default=False,
        verbose_name='Подарок'
    )
    gift_description = models.CharField(
        max_length=100,
        verbose_name='Описание подарка',
        null=True,
        blank=True,
    )
    first_order = models.BooleanField(
        default=False,
        verbose_name='Первый заказ'
    )

    class Meta:
        ordering = ['-created']
        verbose_name = 'промокод'
        verbose_name_plural = 'промокоды'

    def __str__(self):
        return f'{self.title_rus}'

    @classmethod
    def is_valid(cls, promocode):
        now = timezone.now()
        try:
            if (promocode.is_active
                    and
                    promocode.valid_from <= now
                    <= promocode.valid_to):
                return promocode

        except Promocode.DoesNotExist:
            pass

        return False

    def get_promocode_disc(self, request=None, amount=None):
        return get_promocode_discount_amount(self, request=None, amount=None)



class PrivatPromocode(models.Model):
    """ Модель для промокодов."""
    base_profile = models.ForeignKey(
        BaseProfile,
        on_delete=models.CASCADE,
        verbose_name='пользователь'
    )
    promocode = models.ForeignKey(
        Promocode,
        on_delete=models.PROTECT,
        verbose_name='промокод'
    )
    created = models.DateField(
        'Дата добавления', auto_now_add=True
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='активен'
    )
    valid_from = models.DateTimeField(
        'Начало действия'
    )
    valid_to = models.DateTimeField(
        'Окончание действия'
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name='использован'
    )
