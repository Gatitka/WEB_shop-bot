# Generated by Django 4.0 on 2024-02-14 11:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='webaccount',
            name='web_language',
            field=models.CharField(choices=[('en', 'English'), ('ru', 'Russian'), ('sr-latn', 'Serbian')], default='sr-latn', max_length=10, verbose_name='Язык сайта'),
        ),
    ]
