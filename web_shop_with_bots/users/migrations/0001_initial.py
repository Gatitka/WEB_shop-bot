# Generated by Django 4.0 on 2024-02-14 10:02

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import phonenumber_field.modelfields
import users.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('tm_bot', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WEBAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('first_name', models.CharField(max_length=150, validators=[users.validators.validate_first_and_last_name], verbose_name='Имя')),
                ('last_name', models.CharField(max_length=150, validators=[users.validators.validate_first_and_last_name], verbose_name='Фамилия')),
                ('password', models.CharField(max_length=100, validators=[django.core.validators.MinLengthValidator(8)], verbose_name='Пароль')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='Email')),
                ('web_language', models.CharField(choices=[('en', 'English'), ('ru', 'Russian'), ('sr-latn', 'Serbian')], default='RUS', max_length=10, verbose_name='Язык сайта')),
                ('phone', phonenumber_field.modelfields.PhoneNumberField(max_length=128, region=None, unique=True, verbose_name='Телефон')),
                ('notes', models.CharField(blank=True, max_length=400, null=True, verbose_name='Пометки')),
                ('is_active', models.BooleanField(default=False, help_text='Аккаунт активирован.Пользователь перешел по ссылке из письма для активации аккаунта.', verbose_name='active')),
                ('is_deleted', models.BooleanField(default=False, help_text='Был ли аккаунт удален.', verbose_name='deleted')),
            ],
            options={
                'verbose_name': 'Аккаунт сайта',
                'verbose_name_plural': 'Аккаунты сайта',
                'ordering': ['-date_joined'],
            },
        ),
        migrations.CreateModel(
            name='BaseProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(blank=True, max_length=150, null=True, verbose_name='Имя')),
                ('last_name', models.CharField(blank=True, max_length=150, null=True, verbose_name='Фамилия')),
                ('phone', phonenumber_field.modelfields.PhoneNumberField(blank=True, help_text="Внесите телефон, прим. '+38212345678'. Для пустого значения, внесите 'None'.", max_length=128, null=True, region=None, unique=True, verbose_name='телефон')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='email')),
                ('city', models.CharField(blank=True, max_length=20, null=True, verbose_name='Город')),
                ('date_joined', models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')),
                ('notes', models.CharField(blank=True, max_length=400, null=True, verbose_name='Пометки')),
                ('date_of_birth', models.DateField(blank=True, help_text='Формат даты ДД.ММ.ГГГГ.', null=True, verbose_name='День рождения')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активный')),
                ('base_language', models.CharField(choices=[('en', 'English'), ('ru', 'Russian'), ('sr-latn', 'Serbian')], default='sr-latn', max_length=10, verbose_name='Язык')),
                ('messenger_account', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='profile', to='tm_bot.messengeraccount', verbose_name='Мессенджер')),
            ],
            options={
                'verbose_name': 'клиент',
                'verbose_name_plural': 'клиенты',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='UserAddress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(max_length=100, verbose_name='адрес')),
                ('base_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.baseprofile', verbose_name='базовый профиль')),
            ],
            options={
                'verbose_name': 'Мой адрес',
                'verbose_name_plural': 'Мои адреса',
            },
        ),
        migrations.AddField(
            model_name='baseprofile',
            name='my_addresses',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='profile', to='users.useraddress', verbose_name='адреса'),
        ),
        migrations.AddField(
            model_name='baseprofile',
            name='web_account',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='profile', to='users.webaccount', verbose_name='Аккаунт на сайте (web_account)'),
        ),
        migrations.AddField(
            model_name='webaccount',
            name='base_profile',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='users.baseprofile', verbose_name='базовый профиль'),
        ),
        migrations.AddField(
            model_name='webaccount',
            name='groups',
            field=models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups'),
        ),
        migrations.AddField(
            model_name='webaccount',
            name='user_permissions',
            field=models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions'),
        ),
    ]
