# Generated by Django 4.0 on 2024-05-20 09:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery_contacts', '0010_courier'),
    ]

    operations = [
        migrations.AddField(
            model_name='courier',
            name='is_active',
            field=models.BooleanField(default=False, verbose_name='активен'),
        ),
    ]
