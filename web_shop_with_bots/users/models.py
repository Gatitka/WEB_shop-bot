from django.contrib.auth.models import AbstractUser, BaseUserManager
from tm_bot.models import TelegramAccount
# from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

# UserRoles (models.TextChoices):
#     ADMIN = ('admin', 'Администратор')
#     USER = ('user', 'Пользователь')

ADDRESS_TYPE_CHOICES = (
    ("1", "Дом"),
    ("2", "Работа")
)


class UserAddresses(models.Model):
    base_profile = models.ForeignKey(
        'BaseProfile',
        on_delete=models.PROTECT,
        related_name='my_addresses',
        verbose_name='Аккаунт сайта'
        )
    short_name = models.CharField(
        'адрес коротко',
        max_length=20
    )
    full_address = models.CharField(
        'адрес полный',
        max_length=100
    )
    type = models.CharField(
        'тип',
        max_length=100,
        choices=ADDRESS_TYPE_CHOICES
    )

    class Meta:
        ordering = ['-id']
        verbose_name = 'Мой адрес'
        verbose_name_plural = 'Мои адреса'

    def __str__(self):
        return f'Адрес {self.short_name}'


class BaseProfile(models.Model):
    ''' Базовая модель клиента, созданная для сведения клиентов сайта и ботов из соц сетей
    в одну сущность, которая будет хранить данные о клиенте: имя, фамилия, телефон, адрес и пр
    + корзину, заказы.'''

    web_account = models.OneToOneField(
        'WEBAccount',
        on_delete=models.PROTECT,
        related_name='profile',
        verbose_name='Базовый профиль',
        blank=True, null=True
        )
    messenger_account = models.OneToOneField(
        TelegramAccount,
        on_delete=models.PROTECT,
        related_name='profile',
        verbose_name='Мессенджер',
        blank=True, null=True
        )
    city = models.CharField(
        'Город',
        max_length=20,
        blank=True, null=True,
        # выпадающий список
    )
    date_joined = models.DateTimeField(
        'Дата регистрации',
        auto_now_add=True
    )
    notes = models.CharField(
        'Пометки',
        max_length=400,
        blank=True, null=True
    )
    date_of_birth = models.DateField(
        'День рождения',
        blank=True, null=True,
        help_text='Формат даты ДД.ММ.ГГГГ.'
    )
    is_active = models.BooleanField(
        'Активный',
        default=True
    ) # instead of deleting user switch to inactive

    # создать метод очистки сохряняемых данных
    # невозможность удаления пользователя
    base_language = models.CharField(
        'Язык',
        max_length=3,
        choices=settings.LANGUAGE_CHOICES,
        default="RUS"
    )

    @property
    def email(self):
        return self.email

    class Meta:
        ordering = ['-id']
        verbose_name = 'клиент'
        verbose_name_plural = 'клиенты'

    def __str__(self):
        return f'Клиент id = {self.id}'


class CustomWEBAccountManager(BaseUserManager):

    def _create_user(self, email, password=None, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        web_account = self.model(email=email, **extra_fields)
        web_account.set_password(password)
        web_account.save()
        # base_profile = BaseProfile(
        #     web_account=web_account
        # )
        # base_profile.save(using=self._db)
        # web_account.base_profile = base_profile
        # web_account.save()
        return web_account

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_active', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        if extra_fields.get('is_active') is not True:
            raise ValueError('Superuser must have is_active=True.')

        return self._create_user(email, password, **extra_fields)


class WEBAccount(AbstractUser):
    ''' Базовая модель клиента, созданная для сведения клиентов сайта и ботов из соц сетей
    в одну сущность, которая будет хранить данные о клиенте: имя, фамилия, телефон, адрес и пр
    + корзину, заказы.'''
    username = None
    password = models.CharField(
        'Пароль',
        max_length=100,
        validators=[MinLengthValidator(8)]
    )
    email = models.EmailField(
        'Email',
        max_length=254,
        unique=True,
        blank=True, null=True
    )
    web_language = models.CharField(
        'Язык сайта',
        max_length=3,
        choices=settings.LANGUAGE_CHOICES,
        default="RUS"
    )
    phone = models.CharField(
        'Телефон',
        max_length=15,
        validators=[MinLengthValidator(8)],
        # настроить норм валидацию
    )
    notes = models.CharField(
        'Пометки',
        max_length=400,
        blank=True, null=True
    )
    base_profile = models.OneToOneField(
        'BaseProfile',
        on_delete=models.PROTECT,
        verbose_name='базовый профиль',
        blank=True, null=True
        )
    # role = models.CharField(
    #     'Роль',
    #     max_length=9,
    #     choices=UserRoles.choices,
    #     default=UserRoles.USER
    # )

    class Meta:
        ordering = ['-date_joined']
        verbose_name = 'Аккаунт сайта'
        verbose_name_plural = 'Аккаунты сайта'

    # def is_admin(self):
    #     return self.role == UserRoles.ADMIN or self.is_superuser

    # создать метод очистки сохряняемых данных

    def __str__(self):
        return f'{self.email}'

    objects = CustomWEBAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone']


@receiver(post_save, sender=WEBAccount)
def create_base_profile(sender, instance, created, **kwargs):
    if created:
        base_profile=BaseProfile(web_account=instance)
        base_profile.save()
        instance.base_profile = base_profile
        instance.save()


# @receiver(post_save, sender=WEBAccount)
# def save_base_profile(sender, instance, **kwargs):
#     instance.base_profile.save()
