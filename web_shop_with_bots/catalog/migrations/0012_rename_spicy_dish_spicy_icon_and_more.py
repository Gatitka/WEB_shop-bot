# Generated by Django 4.0 on 2023-12-27 14:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0011_dish_spicy_dish_vegan_alter_category_priority_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dish',
            old_name='spicy',
            new_name='spicy_icon',
        ),
        migrations.RenameField(
            model_name='dish',
            old_name='vegan',
            new_name='vegan_icon',
        ),
    ]