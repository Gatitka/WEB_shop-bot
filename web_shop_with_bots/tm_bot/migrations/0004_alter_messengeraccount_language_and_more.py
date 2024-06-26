# Generated by Django 4.0 on 2024-04-30 10:05

import django.core.validators
from django.db import migrations, models
import tm_bot.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tm_bot', '0003_alter_messengeraccount_msngr_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messengeraccount',
            name='language',
            field=models.CharField(choices=[('en', 'English'), ('ru', 'Russian'), ('sr-latn', 'Serbian')], default='sr-latn', max_length=10, verbose_name='язык'),
        ),
        migrations.AlterField(
            model_name='messengeraccount',
            name='msngr_id',
            field=models.CharField(blank=True, help_text='Только для Tm, внесется автоматически.', max_length=100, null=True, validators=[django.core.validators.MinLengthValidator(4)], verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='messengeraccount',
            name='msngr_link',
            field=models.URLField(blank=True, help_text='Ссылка на чат, внесется автоматически.', null=True, verbose_name='Текст ссылки в Чат'),
        ),
        migrations.AlterField(
            model_name='messengeraccount',
            name='msngr_type',
            field=models.CharField(choices=[('tm', 'Telegram'), ('wts', 'WhatsApp'), ('vb', 'Viber')], max_length=3, verbose_name='msngr type  *'),
        ),
        migrations.AlterField(
            model_name='messengeraccount',
            name='msngr_username',
            field=models.CharField(blank=True, help_text="Для Tm username начинается с @. ( прим '@yume_sushi')<br>Для Wts username = номер телефона. (прим '+38212345678')<br>Для Vbr username = номер телефона. (прим '+38212345678')", max_length=100, null=True, validators=[tm_bot.validators.validate_msngr_username], verbose_name='Username  *'),
        ),
        migrations.AlterField(
            model_name='messengeraccount',
            name='subscription',
            field=models.BooleanField(default=True, verbose_name='подписка на рассылки'),
        ),
        migrations.AlterField(
            model_name='messengeraccount',
            name='tm_chat_id',
            field=models.CharField(blank=True, help_text='Только для Tm, внесется автоматически.', max_length=100, null=True, validators=[django.core.validators.MinLengthValidator(4)], verbose_name='Tm_chat_ID'),
        ),
    ]
