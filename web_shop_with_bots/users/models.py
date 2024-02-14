from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
# from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, MinLengthValidator
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from phonenumber_field.modelfields import PhoneNumberField
from .validators import validate_first_and_last_name

from tm_bot.models import MessengerAccount


class UserAddress(models.Model):
    address = models.CharField(
        'адрес',
        max_length=100
    )
    base_profile = models.ForeignKey(
        'BaseProfile',
        on_delete=models.CASCADE,
        verbose_name='базовый профиль',
    )   # НЕ УДАЛЯТЬ! нужен для правильного отображения админки

    class Meta:
        verbose_name = 'Мой адрес'
        verbose_name_plural = 'Мои адреса'

    def __str__(self):
        return f'Адрес {self.address}'


class BaseProfile(models.Model):
    ''' Базовая модель клиента, созданная для сведения клиентов сайта и ботов из соц сетей
    в одну сущность, которая будет хранить данные о клиенте: имя, фамилия, телефон, адрес и пр
    + корзину, заказы.'''

    web_account = models.OneToOneField(
        'WEBAccount',
        on_delete=models.PROTECT,
        related_name='profile',
        verbose_name='Аккаунт на сайте (web_account)',
        blank=True, null=True
        )
    messenger_account = models.OneToOneField(
        MessengerAccount,
        on_delete=models.PROTECT,
        related_name='profile',
        verbose_name='Мессенджер',
        blank=True, null=True
        )
    first_name = models.CharField(
        'Имя',
        max_length=150,
        blank=True, null=True
        )
    last_name = models.CharField(
        'Фамилия',
        max_length=150,
        blank=True, null=True
        )
    phone = PhoneNumberField(
        verbose_name='телефон',
        unique=True,
        blank=True, null=True,
        help_text="Внесите телефон, прим. '+38212345678'. Для пустого значения, внесите 'None'.",
        )
    email = models.EmailField(
        'email',
        blank=True, null=True
        )
    my_addresses = models.ForeignKey(
        'UserAddress',
        on_delete=models.PROTECT,
        related_name='profile',
        verbose_name='адреса',
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
    )  # instead of deleting user switch to inactive

    base_language = models.CharField(
        'Язык',
        max_length=10,
        choices=settings.LANGUAGES,
        default="sr-latn"
    )

    class Meta:
        ordering = ['-id']
        verbose_name = 'клиент'
        verbose_name_plural = 'клиенты'

    def __str__(self):
        return (f'{self.first_name}' if self.first_name is not None else f'Клиент id = {self.id}')


class CustomWEBAccountManager(BaseUserManager):

    def _create_user(self, email, password=None, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        web_account = self.model(email=email, **extra_fields)
        web_account.clean()
        web_account.set_password(password)
        web_account.save()
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
    ''' Модель для зарегистрированного пользователя сайта.
    Имеет привязку к базовому профилю,
    через который осуществляется пополнение корзины и сооздание заказов.

    При тестировании через shell не работали методы clean, а так же create_user.
    Для валидации созданы сигналы перед сохранением.
    '''
    username = None
    first_name = models.CharField(
        'Имя',
        max_length=150,
        validators=[validate_first_and_last_name,]
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=150,
        validators=[validate_first_and_last_name,]
    )
    password = models.CharField(
        'Пароль',
        max_length=100,
        validators=[MinLengthValidator(8)]
    )
    email = models.EmailField(
        'Email',
        max_length=254,
        unique=True
    )
    web_language = models.CharField(
        'Язык сайта',
        max_length=10,
        choices=settings.LANGUAGES,
        default="RUS"
    )
    phone = PhoneNumberField(
        verbose_name='телефон',
        unique=True,
        null=True
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
    is_active = models.BooleanField(
        ('active'),
        default=False,
        help_text=(
            'Аккаунт активирован.'
            'Пользователь перешел по ссылке из письма для активации аккаунта.'
        ),
    )
    is_deleted = models.BooleanField(
        'deleted',
        default=False,
        help_text='Был ли аккаунт удален.'
    )

    class Meta:
        ordering = ['-date_joined']
        verbose_name = 'Аккаунт сайта'
        verbose_name_plural = 'Аккаунты сайта'

    # def is_admin(self):
    #     return self.role == UserRoles.ADMIN or self.is_superuser

    # создать метод очистки сохряняемых данных

    def __str__(self):
        return f'{self.email}'

    def clean(self):
        # if not self.first_name or self.first_name in ['me', 'я', 'ja', 'и']:
        #     raise ValidationError(
        #         {'first_name': "Please provide first_name"})

        # if (not self.last_name
        #     or self.last_name in ['me', 'i', 'я', 'ja', 'и']
        #         or (self.last_name.isalpha() is not True)):

        #     raise ValidationError(
        #         ("Please provide the last_name. "
        #          "Only letters are allowed.")
        #     )
        pass

    objects = CustomWEBAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone']



# ------    сигналы для создания base_profile при создании web account
@receiver(post_save, sender=WEBAccount)
def create_base_profile(sender, instance, created, **kwargs):
    if created:
        if not (BaseProfile.objects.filter(web_account=instance).exists() and
                BaseProfile.objects.filter(phone=instance.phone).exists() and
                BaseProfile.objects.filter(email=instance.email).exists()):
            base_profile = BaseProfile(
                web_account=instance,
                first_name=instance.first_name,
                last_name=instance.last_name,
                phone=instance.phone,
                email=instance.email
            )
        else:
            base_profile = BaseProfile.objects.filter(
                                    phone=instance.phone,
                                    )
            base_profile.web_account = instance
        base_profile.save()
        instance.base_profile = base_profile
        instance.save(update_fields=['base_profile'])


# # ------    сигналы для валидации создания web_account если нет имени или phone
# @receiver(pre_save, sender=WEBAccount)
# def create_web_account(sender, instance, **kwargs):
#     if not instance.phone:
#         raise ValidationError(
#             {'phone': "Please provide phone."})

#     if (not instance.first_name
#         or instance.first_name in ['me', 'i', 'я', 'ja', 'и']
#             or (instance.first_name.isalpha() is not True)):

#         raise ValidationError(
#             {'first_name': ("Please provide first_name. "
#                             "Only letters are allowed.")})

#     if (not instance.last_name
#         or instance.last_name in ['me', 'i', 'я', 'ja', 'и']
#             or (instance.last_name.isalpha() is not True)):

#         raise ValidationError(
#             ("Please provide the last_name. "
#              "Only letters are allowed.")
#         )



#     email_validator = EmailValidator(message='Enter a valid email address.')
#     email_validator(instance.email)
