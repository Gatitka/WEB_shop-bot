# Generated by Django 4.0 on 2024-01-12 13:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0014_alter_dish_options_alter_dish_priority'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dish',
            old_name='add_date',
            new_name='created',
        ),
    ]