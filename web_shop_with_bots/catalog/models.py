from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from pytils.translit import slugify


class Category(models.Model):
    '''Модель категорий блюд.'''
    priority = models.PositiveSmallIntegerField(
        verbose_name='Порядок отображения в меню',
        validators=[MinValueValidator(1)],
        null=True, blank=True
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
    active = models.BooleanField(
        default=False
    )
    slug = models.SlugField(
        max_length=200,
        verbose_name='slug',
        # unique=True,
        help_text=(
            'Укажите уникальный адрес для категории блюд. Используйте только '
            'латиницу, цифры, дефисы и знаки подчёркивания'
        )
    )
    # URLField
    # category_image

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'
        ordering = ('priority',)

    def clean(self) -> None:
        self.name_rus = self.name_rus.strip().lower()
        self.name_srb = self.name_srb.strip().lower()
        return super().clean()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:100]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name_rus


class Dish(models.Model):
    '''Модель блюда.'''
    article = models.IntegerField(
        validators=[MinValueValidator(6)],
        verbose_name='артикул'
    )
    active = models.BooleanField(
        verbose_name='активен',
        default=False
    )
    short_name_rus = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name='Название РУС',
        help_text='Добавьте название блюда.'
    )
    short_name_srb = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name='Название SRB',
        help_text='Добавьте название блюда.'
    )
    text_rus = models.CharField(
        max_length=200,
        verbose_name='Описание РУС',
        help_text='Добавьте описание блюда.'
    )
    text_srb = models.CharField(
        max_length=200,
        verbose_name='Описание SRB',
        help_text='Добавьте описание блюда.'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        verbose_name='Категория',
        related_name='dishes',
        help_text='Добавьте категорию блюда.'
    )
    # image = models.ImageField(
    #     upload_to='recipe/images/',
    #     help_text='Добавьте изображение готового блюда.'
    # )

    # ingredients = models.ManyToManyField(
    #     Ingredient,
    #     through='DishIngredient',
    #     verbose_name='Ингредиенты',
    #     related_name='ingredient',
    #     help_text='Добавьте ингредиенты рецепта.'
    # )

    # discount
    price = models.FloatField(    # цена
        verbose_name='цена',
        validators=[MinValueValidator(0.01)]
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


    class Meta:
        ordering = ['article']
        verbose_name = 'блюдо'
        verbose_name_plural = 'блюда'

    def __str__(self):
        return self.short_name_rus

    # def final_price(self):
    #    price with discount

    # def load_ingredients(self, ingredients):
    #     lst_ingrd = [
    #         DishIngredient(
    #             ingredient=ingredient["id"],
    #             amount=ingredient["amount"],
    #             recipe=self,
    #         )
    #         for ingredient in ingredients
    #     ]
    #     DishIngredient.objects.bulk_create(lst_ingrd)


# class Ingredient(models.Model):
#     """ Модель для описания ингредиентов."""
#     name_rus = models.CharField(
#         max_length=200,
#         db_index=True,
#         verbose_name='Название РУС'
#     )
#     name_srb = models.CharField(
#         max_length=200,
#         db_index=True,
#         verbose_name='Название SRB'
#     )
#     measurement_unit = models.CharField(
#         max_length=24,
#         db_index=True,
#         verbose_name='Ед-ца измерения'
#     )
#     # image

#     class Meta:
#         verbose_name = 'ингредиент'
#         verbose_name_plural = 'ингредиенты'
#         ordering = ('id', )

#     def __str__(self):
#         return self.name_rus

#     def clean(self) -> None:
#         self.name_rus = self.name_rus.strip().lower()
#         self.name_srb = self.name_srb.strip().lower()
#         self.measurement_unit = self.measurement_unit.lower()
#         if Ingredient.objects.filter(name_rus=self.name_rus).exists() or Ingredient.objects.filter(name_srb=self.name_srb).exists():
#             raise ValidationError('Ингредиент с таким названием уже есть')
#         super().clean()


# class DishIngredient(models.Model):
#     """ Модель для сопоставления связи блюда и ингридиентов."""
#     dish = models.ForeignKey(
#         Dish,
#         on_delete=models.CASCADE,
#         verbose_name='Блюдо',
#         related_name='ingredient',
#     )
#     ingredient = models.ForeignKey(
#         Ingredient,
#         on_delete=models.PROTECT,
#         verbose_name='Ингредиент',
#         related_name='dishes'
#     )
#     # amount = models.PositiveSmallIntegerField(
#     #     verbose_name='Кол-во',
#     #     validators=[MinValueValidator(1)]
#     # )

#     class Meta:
#         ordering = ['dish']
#         verbose_name = 'блюдо-ингредиенты'
#         verbose_name_plural = 'блюдо-ингредиенты'
#         constraints = [
#             models.UniqueConstraint(
#                 fields=['dish', 'ingredient'],
#                 name='unique_dish_ingredient'
#             )
#         ]
