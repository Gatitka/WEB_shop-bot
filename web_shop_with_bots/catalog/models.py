from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Max
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields
from pytils.translit import slugify
from django.conf import settings
from delivery_contacts.models import Restaurant
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import re
import os
import unicodedata


class Category(TranslatableModel):
    '''Модель категорий блюд.'''
    translations = TranslatedFields(
        name=models.CharField(
            'название',
            max_length=200,
            blank=True, null=True,
            db_index=True
        ),
        messenger_name=models.CharField(
            'мсдж_название',
            max_length=200,
            blank=True, null=True,
            db_index=True
        )

    )
    priority = models.PositiveSmallIntegerField(
        verbose_name='№ п/п',
        validators=[MinValueValidator(1)],
        blank=True,
        unique=True,
        db_index=True
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='активен'
    )
    slug = models.SlugField(
        max_length=200,
        verbose_name='slug',
        unique=True,
        help_text=(
            'Укажите уникальный адрес для категории блюд. Используйте только '
            'латиницу, цифры, дефисы и знаки подчёркивания'
        ),
        db_index=True
    )

    def clean(self) -> None:
        # self.name = self.name.strip().lower()
        # self.name_srb = self.name_srb.strip().lower()
        # self.name_en = self.name_en.strip().lower()

        return super().clean()

    def save(self, *args, **kwargs):
        if not self.priority:
            max_position = Category.objects.all(
                ).order_by('-priority').values('priority').first()
            self.priority = max_position['priority'] + 1

        if not self.slug:
            self.slug = slugify(self.title)[:100]

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.slug}'

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'
        ordering = ('priority',)


class Dish(TranslatableModel):
    '''Модель блюда.'''
    translations = TranslatedFields(
        short_name=models.CharField(
            'короткое описание *',
            max_length=200,
            db_index=True,
            help_text='Добавьте название блюда. max 200 зн.',
            null=True, blank=True,
        ),
        text=models.CharField(
            'полное описание *',
            max_length=200,
            db_index=True,
            help_text='Добавьте описание блюда. max 200 зн.',
            null=True, blank=True,
        ),
        msngr_short_name=models.CharField(
            'короткое описание',
            max_length=200,
            db_index=True,
            help_text='Добавьте название блюда. max 200 зн.',
            null=True, blank=True,
        ),
        msngr_text=models.CharField(
            'полное описание',
            max_length=200,
            db_index=True,
            help_text='Добавьте описание блюда. max 200 зн.',
            null=True, blank=True,
        )
    )
    id = models.IntegerField(
        unique=True,
        primary_key=False,
        null=True, blank=True,
    )
    article = models.CharField(
        max_length=6,
        verbose_name='артикул *',
        help_text=(
            "Добавьте артикул, пример: '001'.\n"
            "Возможны как цифры, так и буквы."
        ),
        unique=True,
        primary_key=True,
        db_index=True,
    )
    priority = models.PositiveSmallIntegerField(
        verbose_name='№ п/п',
        validators=[MinValueValidator(1)],
        null=True,
        help_text=
            "Порядковый номер отображения в категории, прим. '01'.\n"
            "Проставится автоматически.",
        db_index=True
    )
    is_active = models.BooleanField(
        verbose_name='активен',
        default=False,
        help_text='Активные позиции отображаются на сайте.'
    )
    image = models.ImageField(
        upload_to='menu/dish_images/',
        null=True,
        default=None,
        blank=True,
        verbose_name='Изображение',
        )
    category = models.ManyToManyField(
        Category,
        through='DishCategory',
        help_text='Выберите категории блюда.',
        db_index=True,
    )
    price = models.DecimalField(
        verbose_name='цена, DIN *',
        validators=[MinValueValidator(0.01)],
        help_text='Внесите цену в DIN. Формат 00000.00',
        max_digits=7, decimal_places=2,
        default=Decimal('0'),
    )
    discount = models.DecimalField(
        verbose_name='скидка, %',
        default=None,
        null=True, blank=True,
        help_text="Внесите скидку, прим. для 10% внесите '10,00'.",
        max_digits=6, decimal_places=2
    )
    final_price = models.DecimalField(
        verbose_name='итог цена, DIN',
        validators=[MinValueValidator(0.01)],
        help_text=('Цена после скидок в DIN. Проставится после сохранения.\n'
                   "Показана на сайте."),
        max_digits=8, decimal_places=2,
        default=Decimal('0'),
    )
    final_price_p1 = models.DecimalField(
        verbose_name='цена P1, DIN *',
        validators=[MinValueValidator(0.01)],
        help_text=('Партнер P1 (GLovo/Wolt). Внесите цену в DIN. Формат 00000.00\n'
                   "Не рассчитывается автоматически"),
        max_digits=8, decimal_places=2,
        default=Decimal('0'),
    )
    final_price_p2 = models.DecimalField(
        verbose_name='цена P2, DIN *',
        validators=[MinValueValidator(0.01)],
        help_text=('Партнер P2. Внесите цену в DIN. Формат 00000.00\n'
                   "Не рассчитывается автоматически"),
        max_digits=8, decimal_places=2,
        default=Decimal('0'),
    )
    weight_volume = models.CharField(
        max_length=10,
        default=1,
        verbose_name='Вес/объем всего блюда *',
        help_text='Добавьте вес/объем.'
    )
    weight_volume_uom = models.ForeignKey(
        'UOM',
        verbose_name='ед-цы веса/обема',
        on_delete=models.PROTECT,
        related_name='dishes_weight',
        blank=True, null=True
    )
    units_in_set = models.CharField(
        verbose_name='Количество единиц в блюде *',
        help_text=("Добавьте количество единиц \nв одной позиции. "
                   "Пример: в 1 блюде 8 роллов, вносимое значение будет '8'."),
        max_length=10,
        default=1
    )
    units_in_set_uom = models.ForeignKey(
        'UOM',
        verbose_name='ед-цы кол-ва',
        on_delete=models.PROTECT,
        related_name='dishes_units_in_set',
        blank=True, null=True
    )
    created = models.DateTimeField(
        'Дата добавления',
        auto_now_add=True
    )
    vegan_icon = models.BooleanField(
        verbose_name='🌿 Иконка веган',
        default=False
    )
    spicy_icon = models.BooleanField(
        verbose_name='🌶️ Иконка острое',
        default=False
    )
    utensils = models.PositiveSmallIntegerField(
        verbose_name='приборы',
        help_text="Кол-во приборов в порции.",
        blank=True,
        default=0
    )
    includes_standard_set = models.BooleanField(
        verbose_name="Включает допы",
        help_text=("Включает стандартный набор (соус, имбирь, васаби)\n"
                   "Отображается в карточке блюда."),
        default=True
    )

    def __str__(self):
        name = self.safe_translation_getter("short_name", any_language=True) or ""
        # если вообще нет переводов — покажем только артикул
        return f"{self.article} {name}".strip()

    class Meta:
        ordering = ['pk']
        verbose_name = 'блюдо'
        verbose_name_plural = 'блюда'

    # def clean(self) -> None:
    #     self.short_name = self.short_name.strip().lower()
    #     return super().clean()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_image = self.__dict__.get('image')

    def save(self, *args, **kwargs):
        # 1. назначаем id по порядку, если новый объект
        if not self.id:
            max_id = Dish.objects.aggregate(Max('id'))['id__max'] or 0
            self.id = max_id + 1

        # 2. рассчитываем цены со скидкой
        if self.discount:
            self.final_price = Decimal(
                self.price * Decimal(1 - self.discount/100)
            )
            self._price = self.price
        else:
            self.final_price = self.price

        # было ли изменение картинки
        image_changed = self.image and (self.image != self._original_image)

        # СНАЧАЛА обычное сохранение – чтобы файл попал в media
        super().save(*args, **kwargs)

        # ПОТОМ конвертация
        if image_changed:
            new_path = self._convert_image_to_webp()
            if new_path:
                # обновляем поле image в БД без рекурсии
                type(self).objects.filter(pk=self.pk).update(image=new_path)
                self.image.name = new_path

        # обновляем оригинальное значение
        self._original_image = self.image

    def _convert_image_to_webp(self, quality: int = 80) -> str | None:
        if not self.image:
            return None

        storage = self.image.storage
        old_path = self.image.name  # уже что-то типа 'menu/dish_images/xxx.jpg'

        if not storage.exists(old_path):
            return None

        dirname, filename = os.path.split(old_path)
        stem, ext = os.path.splitext(filename)
        ext = ext.lower()

        if ext == ".webp":
            return None  # уже webp, ничего не делаем

        with storage.open(old_path, "rb") as f:
            img = Image.open(f)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            buffer = BytesIO()
            img.save(buffer, format="WEBP", quality=quality, method=6)
            buffer.seek(0)

        new_filename = stem + ".webp"
        new_path = os.path.join(dirname, new_filename) if dirname else new_filename

        storage.save(new_path, ContentFile(buffer.getvalue()))
        storage.delete(old_path)

        return new_path

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


class DishCityPrice(models.Model):
    """Цена блюда для сайта в конкретном городе.

    Здесь храним именно сайтовую цену: базовая цена, скидка и итоговая
    цена после скидки. Партнерские цены вынесены отдельно, потому что для
    них не нужны base/discount/final.
    """
    dish = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name='city_prices',
        to_field='article',
        verbose_name='блюдо',
    )
    city = models.CharField(
        max_length=20,
        verbose_name='город',
        choices=settings.CITY_CHOICES,
        db_index=True,
    )
    price = models.DecimalField(
        verbose_name='базовая цена сайта, DIN',
        validators=[MinValueValidator(0.01)],
        max_digits=8,
        decimal_places=2,
    )
    discount = models.DecimalField(
        verbose_name='скидка сайта, %',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    final_price = models.DecimalField(
        verbose_name='финальная цена сайта, DIN',
        validators=[MinValueValidator(0.01)],
        max_digits=8,
        decimal_places=2,
        blank=True,
    )

    class Meta:
        ordering = ('dish', 'city')
        verbose_name = 'цена блюда'
        verbose_name_plural = 'цены меню'
        constraints = [
            models.UniqueConstraint(
                fields=['dish', 'city'],
                name='unique_dish_city_site_price',
            )
        ]

    def save(self, *args, **kwargs):
        if self.discount:
            self.final_price = Decimal(
                self.price * Decimal(1 - self.discount / 100)
            ).quantize(Decimal('0.01'))
        else:
            self.final_price = self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.dish_id} / {self.city} / site: {self.final_price}'


class DishPartnerPrice(models.Model):
    """Финальная цена блюда для партнера в конкретном городе."""
    dish = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name='partner_prices',
        to_field='article',
        verbose_name='блюдо',
    )
    city = models.CharField(
        max_length=20,
        verbose_name='город',
        choices=settings.CITY_CHOICES,
        db_index=True,
    )
    partner_category = models.CharField(
        max_length=2,
        choices=settings.PARTNERS_PRICE_CATEGORIES,
    )
    final_price = models.DecimalField(
        verbose_name='финальная цена партнера, DIN',
        validators=[MinValueValidator(0.01)],
        max_digits=8,
        decimal_places=2,
    )

    class Meta:
        ordering = ('dish', 'city', 'partner_category')
        verbose_name = 'цена партнеров'
        verbose_name_plural = 'цены партнеров'
        constraints = [
            models.UniqueConstraint(
                fields=("dish", "city", "partner_category"),
                name="unique_partner_price",
            )
        ]

    def __str__(self):
        return f'{self.dish_id} / {self.city} / {self.partner_category}: {self.final_price}'


class DishCategory(models.Model):
    """ Модель для сопоставления связи рецепта и тэгов."""
    dish = models.ForeignKey(
        Dish,
        on_delete=models.PROTECT,
        related_name='dishcategory',
        to_field='article',
        null=True
    )
    category = models.ForeignKey(
        Category,
        related_name='dishcategory',
        on_delete=models.PROTECT,
    )
    dish_priority = models.PositiveSmallIntegerField(
        verbose_name='№ п/п',
        validators=[MinValueValidator(1)],
        blank=True,
        db_index=True,
        null=True,
        help_text=(
            "Порядковый номер отображения в категории, прим. '01'.\n"
            "Проставится автоматически."),
    )

    class Meta:
        ordering = ['dish']
        verbose_name = _('link dish-category')
        verbose_name_plural = 'связи блюдо-категория'
        constraints = [
            models.UniqueConstraint(
                fields=['dish', 'category'],
                name='unique_dish_category'
            ),
            models.UniqueConstraint(
                fields=['category', 'dish_priority'],
                name='unique_priority_in_category'
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.dish_priority:
            from django.db.models import Max
            db_max = DishCategory.objects.filter(
                category=self.category
            ).aggregate(Max("dish_priority"))["dish_priority__max"] or 0
            self.dish_priority = db_max + 1
        super().save(*args, **kwargs)


class UOM(TranslatableModel):
    '''Ед-цы измерения.'''
    translations = TranslatedFields(
        text=models.CharField(
            'текст для сайта',
            max_length=20,
            help_text='текст ед-цы измерения.',
            blank=True, null=True,
        )
    )
    name = models.CharField(
        'системное название',
        max_length=200,
        unique=True,
        db_index=True,
        help_text='Название внутри системы, не видно на сайте'
    )

    class Meta:
        verbose_name = 'ед-ца измерения'
        verbose_name_plural = 'ед-цы измерения'

    def clean(self) -> None:
        self.text = self.text.strip().lower()
        return super().clean()

    def __str__(self) -> str:
        return f"{self.name}"


class CityDishList(models.Model):
    """ Модель для сопоставления связи блюда и города."""
    city = models.CharField(
        max_length=20,
        verbose_name="город",
        choices=settings.CITY_CHOICES,
    )
    dish = models.ManyToManyField(
        Dish,
    )

    class Meta:
        verbose_name = 'Блюдо / Город'
        verbose_name_plural = 'Блюда / Город'

    def __str__(self) -> str:
        return f"Меню {self.city}"


class RestaurantDishList(models.Model):
    """ Модель для сопоставления связи блюдо - ресторан."""
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.PROTECT,
        verbose_name='ресторан',
        related_name='restaurantdishes',
        blank=True,
        null=True,
    )
    dish = models.ManyToManyField(
        Dish,
    )

    class Meta:
        verbose_name = 'Блюдо / Ресторан'
        verbose_name_plural = 'Блюда / Ресторан'

    def __str__(self) -> str:
        return f"Меню {self.restaurant}"
