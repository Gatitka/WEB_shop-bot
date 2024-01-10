from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from pytils.translit import slugify
from decimal import Decimal


class Category(models.Model):
    '''Модель категорий блюд.'''
    priority = models.PositiveSmallIntegerField(
        verbose_name='Порядок отображения в меню',
        validators=[MinValueValidator(1)],
        blank=True
    )
    name_rus = models.CharField(
        max_length=200,
        verbose_name='Название RUS',
        unique=True
    )
    name_srb = models.CharField(
        max_length=200,
        verbose_name='Название SRB',
        unique=True
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
        )
    )
    # category_image

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'
        ordering = ('priority',)

    def clean(self) -> None:
        self.name_rus = self.name_rus.strip().lower()
        self.name_srb = self.name_srb.strip().lower()
        if Category.objects.filter(name_rus=self.name_rus).exists():
            raise ValidationError('Категория с таким названием уже есть')
        if not self.priority:
            max_position = Category.objects.all().order_by('-priority').values('priority').first()
            self.priority = max_position['priority'] + 1
        return super().clean()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:100]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name_rus


class Dish(models.Model):
    '''Модель блюда.'''
    priority = models.PositiveSmallIntegerField(
        verbose_name='Порядок отображения в меню',
        validators=[MinValueValidator(1)],
        blank=True,
    )
    article = models.CharField(
        max_length=6,
        verbose_name='артикул',
        help_text='Добавьте артикул прим. 0101.'
        # валидация длинны от 4 до 6
    )
    is_active = models.BooleanField(
        verbose_name='активен',
        default=False,
        help_text='Активные позиции виды пользователям.'
    )
    short_name_rus = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name='Название РУС',
        help_text='Добавьте название блюда RUS.'
    )
    short_name_srb = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name='Название SRB',
        help_text='Добавьте название блюда SRB.'
    )
    text_rus = models.CharField(
        max_length=200,
        verbose_name='Описание РУС',
        help_text='Добавьте описание блюда RUS.'
    )
    text_srb = models.CharField(
        max_length=200,
        verbose_name='Описание SRB',
        help_text='Добавьте описание блюда SRB.'
    )
    category = models.ManyToManyField(
        Category,
        through='DishCategory',
        verbose_name='категория',
        help_text='Выберите категории блюда.'
    )
    price = models.DecimalField(
        verbose_name='цена',
        validators=[MinValueValidator(0.01)],
        help_text='Внесите цену, DIN.',
        max_digits=6, decimal_places=2,
        default=Decimal('0'),
    )
    discount = models.DecimalField(
        verbose_name='скидка',
        default=None,
        null=True, blank=True,
        help_text="Внесите скидку, прим. для 10% внесите '10'.",
        max_digits=6, decimal_places=2
    )
    weight = models.CharField(
        max_length=10,
        verbose_name='вес, гр',
        help_text='Добавьте вес в гр.'
    )
    uom = models.CharField(
        max_length=10,
        verbose_name='ед-ца измерения',
        help_text='Добавьте единицы измерения.'
    )
    volume = models.CharField(
        max_length=10,
        verbose_name='объем в ед-це поз',
        help_text='Добавьте объем в единице позиции. Прим, 4 шт.'
    )
    add_date = models.DateTimeField(
        'Дата добавления', auto_now_add=True
    )
    vegan_icon = models.BooleanField(
        verbose_name='веган',
        default=False,
        help_text='иконка веган.',
        null=True, blank=True,
    )
    spicy_icon = models.BooleanField(
        verbose_name='острое',
        default=False,
        help_text='иконка острое.',
        null=True, blank=True,
    )

    # image = models.ImageField(
    #     upload_to='recipe/images/',
    #     help_text='Добавьте изображение готового блюда.'
    # )

    class Meta:
        ordering = ['article']
        verbose_name = 'блюдо'
        verbose_name_plural = 'блюда'

    def __str__(self):
        return self.short_name_rus

    def clean(self) -> None:
        self.short_name_rus = self.short_name_rus.strip().lower()
        self.short_name_srb = self.short_name_srb.strip().lower()
        # self.short_name_en = self.short_name_en.strip().lower()
        if Dish.objects.filter(short_name_rus=self.short_name_rus).exists():
            raise ValidationError('Блюдо с таким названием уже есть')
        if not self.priority:
            max_position = Dish.objects.filter(category=self.category).all().order_by('-priority').values('priority').first()
            self.priority = max_position['priority'] + 1
        return super().clean()

    @property
    def final_price(self):
        if self.discount:
            return Decimal(self.price * Decimal(1 - self.discount/100))

        return self.price


class DishCategory(models.Model):
    """ Модель для сопоставления связи рецепта и тэгов."""
    dish = models.ForeignKey(
        Dish,

        on_delete=models.CASCADE,
        verbose_name='блюдо',
        # related_name='category'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        verbose_name='категория',
        # related_name='dish'
    )

    class Meta:
        ordering = ['dish']
        verbose_name = 'связь блюдо-категория'
        verbose_name_plural = 'связи блюдо-категория'
        constraints = [
            models.UniqueConstraint(
                fields=['dish', 'category'],
                name='unique_dish_category'
            )
        ]
