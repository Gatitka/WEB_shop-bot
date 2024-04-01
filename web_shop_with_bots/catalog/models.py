from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Max
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields
from pytils.translit import slugify


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
        self.name = self.name.strip().lower()
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
        return self.slug

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
            "Добавьте артикул, пример: '0101'.\n"
            "Возможны как цифры, так и буквы."
        ),
        unique=True,
        primary_key=True,
        db_index=True,
    )
    priority = models.PositiveSmallIntegerField(
        verbose_name='№ п/п',
        validators=[MinValueValidator(1)],
        blank=True,
        help_text=
            "Порядковый номер отображения в категории, прим. '01'.\n"
            "Проставится автоматически.",
        db_index=True
    )
    is_active = models.BooleanField(
        verbose_name='активен',
        default=False,
        help_text='Активные позиции виды пользователям.'
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
        help_text='Цена после скидок в DIN. Проставится после сохранения.',
        max_digits=7, decimal_places=2,
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
        verbose_name='Иконка веган',
        default=False,
        null=True, blank=True,
    )
    spicy_icon = models.BooleanField(
        verbose_name='Иконка острое',
        default=False,
        null=True, blank=True,
    )

    # def clean(self) -> None:
    #     self.short_name = self.short_name.strip().lower()
    #     return super().clean()

    def save(self, *args, **kwargs):
        if not self.id:
            max_id = Dish.objects.all().aggregate(Max('id'))
            if max_id['id__max'] is not None:
                self.id = max_id['id__max'] + 1
            else:
                self.id = 1

            if not self.priority:
                max_position = Dish.objects.filter(
                        category=self.category
                    ).all().order_by('-priority').values('priority').first()
                self.priority = max_position['priority'] + 1

        if self.discount:
            self.final_price = Decimal(
                self.price * Decimal(1 - self.discount/100)
            )
        else:
            self.final_price = self.price
        super().save(*args, **kwargs)

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

    def __str__(self):
        return self.short_name
        # print(self.safe_translation_getter('short_name', language_code='ru', any_language=True) or str(self.pk))
        # return self.safe_translation_getter('short_name', language_code='ru', any_language=True) or str(self.pk)

    class Meta:
        ordering = ['pk']
        verbose_name = 'блюдо'
        verbose_name_plural = 'блюда'


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

    class Meta:
        ordering = ['dish']
        verbose_name = _('link dish-category')
        verbose_name_plural = 'связи блюдо-категория'
        constraints = [
            models.UniqueConstraint(
                fields=['dish', 'category'],
                name='unique_dish_category'
            )
        ]


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
