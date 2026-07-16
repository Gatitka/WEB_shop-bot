import os
from io import BytesIO

import random
import string

from django.conf import settings
from django.db import models, IntegrityError
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import (FileExtensionValidator,
                                    MinValueValidator, URLValidator)

from django_summernote.fields import SummernoteTextField
from parler.models import TranslatableModel, TranslatedFields
from random import sample
from string import ascii_letters, digits

from .services import get_promocode_discount_amount
from catalog.models import Dish, Category
from delivery_contacts.models import Restaurant
from tm_bot.models import OrdersBot, MessengerAccount
from users.models import BaseProfile


import logging

logger = logging.getLogger(__name__)


class PromoNews(TranslatableModel):
    """ Модель для промо новостей."""
    translations = TranslatedFields(
        title=SummernoteTextField(),
        full_text=SummernoteTextField(),
        # title=models.TextField(
        #     max_length=100,
        #     verbose_name='заголовок',
        #     blank=True, null=True
        # ),
        # full_text=models.TextField(
        #     max_length=600,
        #     verbose_name='описание',
        #     blank=True, null=True
        # ),
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
    image_ru = models.FileField(
            upload_to='promo/',
            verbose_name='изображение ru',
            blank=True, null=True
    )
    image_en = models.FileField(
            upload_to='promo/',
            verbose_name='изображение en',
            blank=True, null=True
    )
    image_sr_latn = models.FileField(
            upload_to='promo/',
            verbose_name='изображение sr-latn',
            blank=True, null=True
    )
    slug = models.SlugField(
        'slug',
        max_length=100,
        unique=True,
        help_text='Используется для ссылки вида /promo?news=<slug>/'
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
        verbose_name = 'новость на сайте'
        verbose_name_plural = 'Новости на сайте'

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
        verbose_name = "Промокод личн"
        verbose_name_plural = "Промокоды личн"


class PromoBroadcast(models.Model):
    """Информационная рассылка по мессенджеру (Telegram)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        SENDING = "sending", "Отправляется"
        DONE = "done", "Отправлено"
        ERROR = "error", "Ошибка"

    title = models.CharField(
        "Название",
        max_length=255,
        help_text="Внутреннее название рассылки для отображения в админке.",
    )
    body = SummernoteTextField(
        "Текст сообщения",
        help_text=mark_safe(escape(
            "Текст рассылки для Telegram. Допустимое форматирование:\n"
            "• Жирный '<b></b>'     • Подчёркивание '<u></u>'\n"
            "• Курсив '<i></i>'     • Ссылки '<a></a>'\n\n"
            "⚠️ Другие HTML-теги не поддерживаются Telegram и будут автоматически удалены."
        ).replace("\n", "<br>")),
    )

    # единственный из «маркетинговых» флажков, который решили оставить
    disable_link_preview = models.BooleanField(
        "Отключить превью ссылок",
        default=False,
        help_text="Если включено — Telegram не будет показывать превью для ссылок.",
    )

    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    sent_at = models.DateTimeField("Отправлено", blank=True, null=True)

    total_recipients = models.PositiveIntegerField(
        "Всего получателей", default=0, editable=False
    )
    delivered_count = models.PositiveIntegerField(
        "Доставлено", default=0, editable=False
    )
    # 🔹 ВАЖНО: только ссылка на бота, без токена
    bot = models.ForeignKey(
        OrdersBot,
        verbose_name="Бот",
        on_delete=models.PROTECT,
        related_name="promo_broadcasts",
        help_text="Через какого бота выполнять рассылку",
    )

    image = models.ImageField(
        "Картинка для рассылки",
        upload_to="promo_broadcasts/",
        blank=True,
        null=True,
        help_text=(
            "Опционально. Если указана только картинка — уйдёт только фото. "
            "Если картинка и текст — текст будет подписью (caption).\n"
            "Рекомендуемые форматы: JPG или PNG, до ~5 МБ."
        ),
    )

    add_inline_keyboard = models.BooleanField(
        "Добавить inline клавиатуру",
        default=False,
        help_text=(
            "Если включено — под сообщением прикрепятся заданные кнопки (писать кодом)"
        ),
    )
    add_reply_keyboard = models.BooleanField(
        "Добавить reply клавиатуру",
        default=False,
        help_text=(
            "Если включено — при получении сообщения внизу экрана появятся кнопки (писать кодом)"
        ),
    )
    processed_count = models.PositiveIntegerField(
        "Пользователей обработано",
        default=0
    )
    results_json = models.JSONField(
        "Результат рассылки",
        default=dict, blank=True
    )
    report_file = models.FileField(
        upload_to="broadcast_reports/",
        blank=True,
        null=True,
        verbose_name="Отчет по рассылке",
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"

    def __str__(self):
        return self.title

    @property
    def city(self):
        # удобно, чтобы и в админке, и в коде быстро понять "город рассылки"
        return getattr(self.bot, "city", None)
    city.fget.short_description = "Город"

    @property
    def delivered_display(self) -> str:
        if not self.total_recipients:
            return "—"
        return f"{self.delivered_count} из {self.total_recipients}"
    delivered_display.fget.short_description = "Доставлено"

    def admin_photo(self):
        if self.image:
            return mark_safe(
                '<img src="{}" width="100" />'.format(self.image.url)
                )
        missing_image_url = "icons/missing_image.jpg"
        return mark_safe(
            '<img src="{}" width="100" />'.format(missing_image_url)
            )

    admin_photo.short_description = 'Image'
    admin_photo.allow_tags = True


class Campaign(models.Model):
    """Модель для рекламных компаний."""
    name = models.CharField(
        "Название кампании",
        max_length=100
    )
    code = models.CharField(
        "Код",
        max_length=10,
        blank=True, null=True,
        unique=True
    )
    created = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )
    city = models.CharField(
        max_length=20,
        verbose_name="город *",
        choices=settings.CITY_CHOICES,
        default=settings.DEFAULT_CITY
    )
    link = models.URLField(
        'Текст ссылки на рекламу',
        blank=True, null=True,
        help_text="Ссылка на бота со стартовым параметром (вносится автоматически)."
    )
    bot = models.ForeignKey(
        OrdersBot,
        on_delete=models.PROTECT,
        help_text="Для какого бота сгенерирован источник",
        verbose_name='Бот',
        related_name='campaigns',
    )
    new_users = models.IntegerField(
        verbose_name='Новых пользователей',
        blank=True, null=True
    )

    class Meta:
        ordering = ['-created']
        verbose_name = 'Источник'
        verbose_name_plural = 'Источники'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self._generate_campaign_code()
            self._generate_campaign_link()
        try:
            return super().save(*args, **kwargs)
        except IntegrityError as e:
            # редкий случай коллизии unique(code) — пробуем пересоздать код 3 раза
            for _ in range(3):
                self._generate_unique_code()
                self._generate_campaign_link()
                try:
                    return super().save(*args, **kwargs)
                except IntegrityError:
                    continue
            logger.error(f"Не удалось сохранить Campaign после ретраев: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Ошибка при сохранении Campaign: {e}", exc_info=True)
            raise

    def _generate_campaign_code(self):
        # Генерирует код
        symbols = ascii_letters + digits
        random_str = sample(symbols, 10)
        print(''.join(random_str))
        self.code = ''.join(random_str)

    def _generate_campaign_link(self):
        # Генерирует ссылку на источник для бота Telegram
        self.link = (
                f"{self.bot.link}?start={self.code}"
            )


class CampaignOpenEvent(models.Model):
    """Модель для записи пар источник-пользователь,
    чтобы считать всего переходы, уникальные и новые."""

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='open_events',
        verbose_name='источник',
    )
    user = models.ForeignKey(
        MessengerAccount,
        on_delete=models.CASCADE,
        related_name='open_events',
        verbose_name='пользователь',
    )
    created = models.DateTimeField(
        'время',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'переход'
        verbose_name_plural = 'переходы'


class Banner(models.Model):

    class ActionType(models.TextChoices):
        DISH       = 'dish',       'Блюдо — открыть карточку'
        CATEGORY   = 'category',   'Категория — открыть список'
        INTERNAL   = 'internal',   'Внутренняя ссылка'
        EXTERNAL   = 'external',   'Внешняя ссылка'
        MODAL_SVG  = 'modal_svg',  'Модальное окно (SVG или картинка)'
        NONE       = 'none',       'Некликабельный'

    # ---- Основное ----
    title = models.CharField(
        'название (внутреннее)',
        max_length=200,
        help_text='Только для админки, не отображается на сайте.'
    )
    city = models.CharField(
        'город',
        max_length=40,
        choices=settings.CITY_CHOICES,
        db_index=True,
    )
    priority = models.PositiveSmallIntegerField(
        'порядок в карусели',
        help_text='Чем меньше число — тем раньше показывается.',
        db_index=True,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField('активен', default=False)

    active_from  = models.DateTimeField('показывать с',  null=True, blank=True)
    active_until = models.DateTimeField('показывать до', null=True, blank=True)

    # ---- Изображение баннера (карточка в карусели) ----
    _IMAGE_VALIDATORS = [
        FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
    ]
    _IMAGE_HELP = (
        'Квадратная карточка в карусели баннеров.<br>'
        '<b>Размер:</b> 600×600 px (минимум 400×400 px).<br>'
        '<b>Соотношение сторон:</b> 1:1 (квадрат, допуск ±15%).<br>'
        '<b>Формат:</b> JPG или PNG — конвертируется в WebP автоматически.<br>'
        '<b>Вес файла:</b> до 500 KB.<br>'
        '<b>Важно:</b> ключевой контент размещайте в центре '
        'с отступом ~15% от каждого края.'
    )

    image = models.ImageField(
        'баннер (SR — дефолт)',
        upload_to='banners/',
        validators=_IMAGE_VALIDATORS,
        help_text=(
            '<b>Дефолтная картинка (сербский).</b> '
            'Используется для всех языков, если не загружены ru/en варианты.<br>'
            + _IMAGE_HELP
        )
    )
    image_ru = models.ImageField(
        'баннер RU',
        upload_to='banners/',
        blank=True, null=True,
        validators=_IMAGE_VALIDATORS,
        help_text='Переопределение для русского языка.<br>' + _IMAGE_HELP,
    )
    image_en = models.ImageField(
        'баннер EN',
        upload_to='banners/',
        blank=True, null=True,
        validators=_IMAGE_VALIDATORS,
        help_text='Переопределение для английского языка.<br>' + _IMAGE_HELP,
    )

    # ---- Действие при клике ----
    action_type = models.CharField(
        'действие при клике',
        max_length=20,
        choices=ActionType.choices,
        default=ActionType.NONE,
    )

    # action_type = DISH
    dish = models.ForeignKey(
        Dish,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='блюдо',
        related_name='banners',
        help_text='Заполните если action_type = «Блюдо».',
    )

    # action_type = CATEGORY
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='категория',
        related_name='banners',
        help_text='Заполните если action_type = «Категория».',
    )

    # action_type = INTERNAL
    # action_type = EXTERNAL
    url = models.CharField(
        'ссылка (внешняя/внутренняя)',
        blank=True,
        max_length=200,
        help_text=(
            "Укажите ссылку в зависимости от выбранного типа действия. <br>"
            "Для внешней ссылки — полный URL (например, https://example.com). <br>"
            "Для внутренней — относительную ссылку без домена (например, /menu или /catalog/pizza)."
        ),
    )

    # action_type = MODAL_SVG — SVG с зашитым контентом (условия акций, ДР)
    _MODAL_FILE_VALIDATORS = [
        FileExtensionValidator(
            allowed_extensions=['svg', 'jpg', 'jpeg', 'png', 'webp']
        )
    ]

    _MODAL_FILE_HELP = (
        'Файл модального окна с промо-информацией: условия акции, ДР и т.п.<br>'
        '<b>Форматы:</b> SVG, JPG, JPEG, PNG или WebP.<br>'
        '<b>Рекомендуемый размер:</b> до 1200 px по ширине.<br>'
        '<b>Вес файла:</b> желательно до 1–1.5 MB.<br>'
        '<b>Важно:</b> файлы 2+ MB могут не загрузиться или работать нестабильно.<br>'
        'Используйте более лёгкие / low-resolution версии изображений.'
    )

    modal_svg = models.FileField(
        'Файл модального окна (SR — дефолт)',
        upload_to='banners/svg/',
        blank=True, null=True,
        validators=_MODAL_FILE_VALIDATORS,
        help_text=(
            '<b>Дефолтный SVG (сербский).</b> '
            'Используется для всех языков, если не загружены ru/en варианты.<br>'
            + _MODAL_FILE_HELP
        ),
    )
    modal_svg_ru = models.FileField(
        'Файл модального окна RU',
        upload_to='banners/svg/',
        blank=True, null=True,
        validators=_MODAL_FILE_VALIDATORS,
        help_text='Переопределение для русского языка.<br>' + _MODAL_FILE_HELP,
    )
    modal_svg_en = models.FileField(
        'Файл модального окна EN',
        upload_to='banners/svg/',
        blank=True, null=True,
        validators=_MODAL_FILE_VALIDATORS,
        help_text='Переопределение для английского языка.<br>' + _MODAL_FILE_HELP,
    )

    # action_type = MODAL_SVG — картинка-постер
    # modal_image = models.ImageField(
    #     'картинка для модального окна',
    #     upload_to='banners/modal/',
    #     blank=True, null=True,
    #     validators=[
    #         FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
    #     ],
    #     help_text=(
    #         'Картинка-постер, открывается поверх страницы при клике.<br>'
    #         '<b>Размер:</b> 1080×1920 px или 900×1200 px.<br>'
    #         '<b>Соотношение сторон:</b> 3:4 или 9:16 (вертикальное).<br>'
    #         '<b>Формат:</b> JPG или PNG — конвертируется в WebP автоматически.<br>'
    #         '<b>Вес файла:</b> до 500 KB.<br>'
    #         '<b>Важно:</b> внизу оставьте ~100 px свободного места '
    #         'под кнопку закрытия.<br>'
    #         'Заполните <b>modal_svg</b> или <b>modal_image</b> (не оба сразу).'
    #     ),
    # )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='ресторан',
        related_name='banners',
    )

    created = models.DateTimeField('создан', auto_now_add=True)
    updated = models.DateTimeField('обновлён', auto_now=True)

    class Meta:
        verbose_name = 'баннер'
        verbose_name_plural = 'баннеры'
        ordering = ['city', 'priority']
        constraints = [
            models.UniqueConstraint(
                fields=['city', 'priority'],
                name='unique_banner_priority_per_city',
            ),
        ]
        permissions = [
            ("edit_banners_Beograd", "Can ADD/CHANGE/DELETE banners Beograd"),
            ("edit_banners_NoviSad", "Can  NoviSad"),
        ]

    def __str__(self):
        return f'[{self.city}] #{self.priority} {self.title}'

    # ------------------------------------------------------------------ #
    #  Валидация                                                           #
    # ------------------------------------------------------------------ #

    def _validate_image_dimensions(self, image_field, min_w, min_h,
                                   expected_ratio, ratio_tolerance, max_kb):
        """Универсальный валидатор размера, пропорций и веса изображения."""
        from PIL import Image as PilImage

        if image_field.size > max_kb * 1024:
            raise ValidationError(
                f'Файл слишком большой: {image_field.size // 1024} KB. '
                f'Максимум {max_kb} KB.'
            )

        img = PilImage.open(image_field)
        w, h = img.size

        if w < min_w or h < min_h:
            raise ValidationError(
                f'Минимальный размер {min_w}×{min_h} px. '
                f'Загружено: {w}×{h} px.'
            )

        ratio = w / h
        if abs(ratio - expected_ratio) > ratio_tolerance:
            raise ValidationError(
                f'Неверное соотношение сторон: ожидается {expected_ratio:.2f} '
                f'(допуск ±{ratio_tolerance}). '
                f'Загружено: {w}×{h} (соотношение {ratio:.2f}).'
            )

    def clean(self):
        super().clean()

        # --- изображения баннера (дефолт + языковые варианты) ---
        for field_name in ('image', 'image_ru', 'image_en'):
            field = getattr(self, field_name)
            if field and not isinstance(field.file, str):
                try:
                    self._validate_image_dimensions(
                        field,
                        min_w=400, min_h=400,
                        expected_ratio=1.0,
                        ratio_tolerance=0.15,
                        max_kb=500,
                    )
                except ValidationError as e:
                    raise ValidationError({field_name: e.messages})

        # # --- картинка модального окна ---
        # if self.modal_image and not isinstance(self.modal_image.file, str):
        #     try:
        #         self._validate_image_dimensions(
        #             self.modal_image,
        #             min_w=900, min_h=1200,
        #             expected_ratio=3 / 4,
        #             ratio_tolerance=0.2,
        #             max_kb=500,
        #         )
        #     except ValidationError as e:
        #         raise ValidationError({'modal_image': e.messages})

        # --- проверка обязательных полей под action_type ---
        checks = {
            self.ActionType.DISH:       ('dish',        'Выберите блюдо.'),
            self.ActionType.CATEGORY:   ('category',    'Выберите категорию.'),
            self.ActionType.INTERNAL:   ('url',         'Укажите внутреннюю ссыку.'),
            self.ActionType.EXTERNAL:   ('url',         'Укажите внешнюю ссылку.'),
        }
        if self.action_type in checks:
            field, msg = checks[self.action_type]
            if not getattr(self, field) and not getattr(self, f'{field}_id', None):
                raise ValidationError({field: msg})

        # проверяем поле с сылкой
        if self.url:
            if self.action_type == self.ActionType.EXTERNAL:
                try:
                    URLValidator()(self.url)
                except ValidationError:
                    raise ValidationError({
                        "url": "Для внешней ссылки укажите корректный URL."
                    })

            elif self.action_type == self.ActionType.INTERNAL:
                if not self.url.startswith("/"):
                    raise ValidationError({
                        "url": (
                            "Для внутренней ссылки укажите относительный путь, "
                            "например: /menu или /catalog/pizza."
                        )
                    })

        if self.action_type == self.ActionType.MODAL_SVG:
            if not self.modal_svg:
                raise ValidationError(
                    {'modal_svg': 'Для модального окна загрузите файл: SVG, JPG, PNG или WebP.'}
                )

         # --- чистим поля, которые не относятся к выбранному action_type ---
        if self.action_type != self.ActionType.DISH:
            self.dish = None

        if self.action_type != self.ActionType.CATEGORY:
            self.category = None

        if (self.action_type != self.ActionType.EXTERNAL
                and self.action_type != self.ActionType.INTERNAL):
            self.url = ""

        if self.action_type != self.ActionType.MODAL_SVG:
            self.modal_svg = None
            self.modal_svg_ru = None
            self.modal_svg_en = None


    # ------------------------------------------------------------------ #
    #  Конвертация в WebP                                                  #
    # ------------------------------------------------------------------ #

    def _convert_to_webp(self, image_field, quality=85):
        """Конвертирует изображение поля в WebP. Возвращает новый путь или None."""
        from PIL import Image as PilImage

        if not image_field:
            return None

        storage = image_field.storage
        old_path = image_field.name

        if not storage.exists(old_path):
            return None

        _, ext = os.path.splitext(old_path)
        if ext.lower() == '.webp':
            return None

        dirname, filename = os.path.split(old_path)
        stem = os.path.splitext(filename)[0]
        new_path = os.path.join(dirname, stem + '.webp') if dirname else stem + '.webp'

        with storage.open(old_path, 'rb') as f:
            img = PilImage.open(f)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            buffer = BytesIO()
            img.save(buffer, format='WEBP', quality=quality, method=6)
            buffer.seek(0)

        storage.save(new_path, ContentFile(buffer.getvalue()))
        storage.delete(old_path)
        return new_path

    # поля изображений баннера, которые конвертируются в WebP
    _IMAGE_FIELDS = ('image', 'image_ru', 'image_en')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self._IMAGE_FIELDS:
            setattr(self, f'_orig_{f}', self.__dict__.get(f))

    def save(self, *args, **kwargs):
        self.full_clean()
        # проставляем номер, если поле пришло пустым
        if self.pk is None or self.priority is None:
            max_priority = (
                type(self).objects
                .filter(city=self.city)
                .aggregate(models.Max('priority'))['priority__max'] or 0
            )
            self.priority = max_priority + 1

        super().save(*args, **kwargs)

        # конвертируем в WebP только изменившиеся image-поля
        update_fields = {}
        for f in self._IMAGE_FIELDS:
            field = getattr(self, f)
            orig = getattr(self, f'_orig_{f}')
            if field and field != orig:
                new_path = self._convert_to_webp(field)
                if new_path:
                    update_fields[f] = new_path
                    field.name = new_path

        if update_fields:
            type(self).objects.filter(pk=self.pk).update(**update_fields)

        # обновляем оригиналы
        for f in self._IMAGE_FIELDS:
            setattr(self, f'_orig_{f}', getattr(self, f))
