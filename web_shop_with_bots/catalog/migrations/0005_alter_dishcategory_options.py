# Generated by Django 4.0 on 2024-01-25 12:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0004_alter_category_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='dishcategory',
            options={'ordering': ['dish'], 'verbose_name': 'link dish-category', 'verbose_name_plural': 'связи блюдо-категория'},
        ),
    ]