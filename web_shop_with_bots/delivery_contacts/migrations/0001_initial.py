# Generated by Django 4.0 on 2023-12-15 21:12

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Delivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_rus', models.CharField(db_index=True, max_length=200, verbose_name='Название РУС')),
                ('name_srb', models.CharField(db_index=True, max_length=200, verbose_name='Название SRB')),
                ('name_en', models.CharField(db_index=True, max_length=200, verbose_name='Название EN')),
                ('type', models.CharField(choices=[('1', 'Доставка'), ('2', 'Самовывоз')], max_length=1, verbose_name='тип')),
                ('is_active', models.BooleanField(default=False)),
                ('price', models.FloatField(blank=True, null=True, verbose_name='цена')),
                ('min_price', models.FloatField(blank=True, null=True, verbose_name='min_цена_заказа')),
                ('description_rus', models.CharField(blank=True, max_length=400, null=True, verbose_name='Описание РУС')),
                ('description_srb', models.CharField(blank=True, max_length=400, null=True, verbose_name='Описание SRB')),
                ('description_en', models.CharField(blank=True, max_length=400, null=True, verbose_name='Описание EN')),
                ('city', models.CharField(max_length=20, verbose_name='город')),
            ],
            options={
                'verbose_name': 'доставка',
                'verbose_name_plural': 'доставка',
            },
        ),
        migrations.CreateModel(
            name='Shop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('short_name', models.CharField(max_length=20, verbose_name='название')),
                ('address_rus', models.CharField(max_length=200, verbose_name='описание_РУС')),
                ('address_en', models.CharField(max_length=200, verbose_name='описание_EN')),
                ('address_srb', models.CharField(max_length=200, verbose_name='описание_SRB')),
                ('work_hours', models.CharField(max_length=100, verbose_name='время работы')),
                ('phone', models.CharField(max_length=100, verbose_name='телефон')),
                ('admin', models.CharField(blank=True, max_length=100, null=True, verbose_name='админ')),
                ('is_active', models.BooleanField(default=False)),
                ('city', models.CharField(blank=True, max_length=50, null=True, verbose_name='город')),
            ],
            options={
                'verbose_name': 'ресторан',
                'verbose_name_plural': 'рестораны',
            },
        ),
    ]