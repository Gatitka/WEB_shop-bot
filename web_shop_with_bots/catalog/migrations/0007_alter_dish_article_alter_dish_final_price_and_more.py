# Generated by Django 4.0 on 2024-02-28 13:57

from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0006_alter_dishcategory_dish'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dish',
            name='article',
            field=models.CharField(db_index=True, help_text="Добавьте артикул, пример: '0101'.\nВозможны как цифры, так и буквы.", max_length=6, primary_key=True, serialize=False, unique=True, verbose_name='артикул *'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='final_price',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), help_text='Цена после скидок в DIN. Проставится после сохранения.', max_digits=7, validators=[django.core.validators.MinValueValidator(0.01)], verbose_name='итог цена, DIN'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='price',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), help_text='Внесите цену в DIN. Формат 00000.00', max_digits=7, validators=[django.core.validators.MinValueValidator(0.01)], verbose_name='цена, DIN *'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='priority',
            field=models.PositiveSmallIntegerField(blank=True, db_index=True, help_text="Порядковый номер отображения в категории, прим. '01'.\nПроставится автоматически.", validators=[django.core.validators.MinValueValidator(1)], verbose_name='№ п/п'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='spicy_icon',
            field=models.BooleanField(blank=True, default=False, null=True, verbose_name='Иконка острое'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='units_in_set',
            field=models.CharField(default=1, help_text="Добавьте количество единиц \nв одной позиции. Пример: в 1 блюде 8 роллов, вносимое значение будет '8'.", max_length=10, verbose_name='Количество единиц в блюде *'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='units_in_set_uom',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='dishes_units_in_set', to='catalog.uom', verbose_name='ед-цы кол-ва'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='vegan_icon',
            field=models.BooleanField(blank=True, default=False, null=True, verbose_name='Иконка веган'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='weight_volume',
            field=models.CharField(default=1, help_text='Добавьте вес/объем.', max_length=10, verbose_name='Вес/объем всего блюда *'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='weight_volume_uom',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='dishes_weight', to='catalog.uom', verbose_name='ед-цы веса/обема'),
        ),
        migrations.AlterField(
            model_name='dishtranslation',
            name='msngr_short_name',
            field=models.CharField(blank=True, db_index=True, help_text='Добавьте название блюда. max 200 зн.', max_length=200, null=True, verbose_name='короткое описание'),
        ),
        migrations.AlterField(
            model_name='dishtranslation',
            name='msngr_text',
            field=models.CharField(blank=True, help_text='Добавьте описание блюда. max 200 зн.', max_length=200, null=True, verbose_name='полное описание'),
        ),
        migrations.AlterField(
            model_name='dishtranslation',
            name='short_name',
            field=models.CharField(blank=True, db_index=True, help_text='Добавьте название блюда. max 200 зн.', max_length=200, null=True, verbose_name='короткое описание *'),
        ),
        migrations.AlterField(
            model_name='dishtranslation',
            name='text',
            field=models.CharField(blank=True, help_text='Добавьте описание блюда. max 200 зн.', max_length=200, null=True, verbose_name='полное описание *'),
        ),
    ]