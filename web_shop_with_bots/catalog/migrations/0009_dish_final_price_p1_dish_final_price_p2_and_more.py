# Generated by Django 4.0 on 2024-05-17 11:20

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0008_alter_dish_article'),
    ]

    operations = [
        migrations.AddField(
            model_name='dish',
            name='final_price_p1',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), help_text='Партнер 1 (GLovo). Внесите цену в DIN. Формат 00000.00', max_digits=7, validators=[django.core.validators.MinValueValidator(0.01)], verbose_name='цена P1, DIN *'),
        ),
        migrations.AddField(
            model_name='dish',
            name='final_price_p2',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), help_text='Партнер 2 (Wolt). Внесите цену в DIN. Формат 00000.00', max_digits=7, validators=[django.core.validators.MinValueValidator(0.01)], verbose_name='цена P2, DIN *'),
        ),
        migrations.AddField(
            model_name='dish',
            name='utensils',
            field=models.PositiveSmallIntegerField(blank=True, help_text='Кол-во приборов в порции.', null=True, verbose_name='приборы'),
        ),
        migrations.AlterField(
            model_name='dishtranslation',
            name='msngr_text',
            field=models.CharField(blank=True, db_index=True, help_text='Добавьте описание блюда. max 200 зн.', max_length=200, null=True, verbose_name='полное описание'),
        ),
        migrations.AlterField(
            model_name='dishtranslation',
            name='text',
            field=models.CharField(blank=True, db_index=True, help_text='Добавьте описание блюда. max 200 зн.', max_length=200, null=True, verbose_name='полное описание *'),
        ),
    ]