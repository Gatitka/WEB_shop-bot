# Generated by Django 4.0 on 2024-02-10 18:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery_contacts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deliverytranslation',
            name='description',
            field=models.TextField(blank=True, max_length=400, null=True, verbose_name='Описание'),
        ),
    ]
