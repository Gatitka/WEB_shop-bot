# Generated by Django 4.0 on 2024-01-26 12:36

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0006_alter_categorytranslation_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='priority',
            field=models.PositiveSmallIntegerField(blank=True, db_index=True, unique=True, validators=[django.core.validators.MinValueValidator(1)], verbose_name='№ п/п'),
        ),
        migrations.AlterField(
            model_name='categorytranslation',
            name='name',
            field=models.CharField(blank=True, db_index=True, max_length=200, null=True, unique=True, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='article',
            field=models.CharField(db_index=True, help_text="Добавьте артикул, прим. '0101'.", max_length=6, verbose_name='артикул'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='category',
            field=models.ManyToManyField(db_index=True, help_text='Выберите категории блюда.', through='catalog.DishCategory', to='catalog.Category'),
        ),
        migrations.AlterField(
            model_name='dish',
            name='priority',
            field=models.PositiveSmallIntegerField(blank=True, db_index=True, help_text="Порядковый номер отображения в категории, прим. '01'.", validators=[django.core.validators.MinValueValidator(1)], verbose_name='№ п/п'),
        ),
    ]