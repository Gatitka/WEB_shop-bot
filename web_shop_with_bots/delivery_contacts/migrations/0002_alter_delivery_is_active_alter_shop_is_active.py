# Generated by Django 4.0 on 2023-12-18 12:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery_contacts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='delivery',
            name='is_active',
            field=models.BooleanField(default=False, verbose_name='активен'),
        ),
        migrations.AlterField(
            model_name='shop',
            name='is_active',
            field=models.BooleanField(default=False, verbose_name='активен'),
        ),
    ]
