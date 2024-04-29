import random
import string

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields
from django.core.validators import MinValueValidator
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
    min_order_amount = models.DecimalField(
        verbose_name='MIN сумма заказа, RSD',
        validators=[MinValueValidator(0.01)],
        max_digits=7, decimal_places=2,
        help_text='Внесите цену в RSD. Формат 00000.00',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created']
        verbose_name = _('promocode')
        verbose_name_plural = _('promocodes')

    def __str__(self):
        return self.title_rus

    def is_active_wthn_timespan(self):
        now = timezone.now()

        if (self.is_active
                and self.valid_from <= now <= self.valid_to):

            return self

        return False

    def get_promocode_disc(self, request=None, amount=None):
        return get_promocode_discount_amount(self, request=None, amount=None)

    def save(self, *args, **kwargs):
        if not self.code:  # Проверяем, был ли предоставлен код промокода
            # Генерируем новый рандомный код промокода
            self.code = self.generate_promocode()
        super().save(*args, **kwargs)

    def generate_promocode(self, length=8):
        """Генерация рандомного кода промокода."""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choice(chars) for _ in range(length))
            if not Promocode.objects.filter(
                        code=code, is_active=True).exists():
                # Проверяем, не существует ли уже такого кода
                return code


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

    class Meta:
        ordering = ['-created']
        verbose_name = _('privat_promocode')
        verbose_name_plural = _('privat_promocodes')
