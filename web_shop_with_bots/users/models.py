from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.gis.db.models import PointField
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from django.conf import settings
from delivery_contacts.utils import (
    google_validate_address_and_get_coordinates,
    parce_coordinates)
from tm_bot.models import MessengerAccount
import logging
from .validators import (validate_birthdate, validate_first_and_last_name,
                         coordinates_validator)
from django.db.models import Sum
from delivery_contacts.models import Restaurant


logger = logging.getLogger(__name__)


class UserRoles(models.TextChoices):
    ADMIN = ('admin', 'Администратор')
    USER = ('user', 'Пользователь')


class UserAddress(models.Model):
    city = models.CharField(
        max_length=40,
        verbose_name="город *",
        choices=settings.CITY_CHOICES,
        default=settings.DEFAULT_CITY,
        blank=True, null=True,
    )
    address = models.CharField(
        'адрес',
        max_length=400
    )
    base_profile = models.ForeignKey(
        'BaseProfile',
        on_delete=models.CASCADE,
        verbose_name='базовый профиль',
        related_name='addresses'
    )   # НЕ УДАЛЯТЬ! нужен для правильного отображения админки
    point = PointField(
        blank=True,
        null=True,
        verbose_name='координаты'
    )
    coordinates = models.CharField(
        max_length=60,
        blank=True,
        null=True,
        verbose_name='координаты ШИР (lat), ДОЛ (lon)',
        help_text=(
            'прим. "44.809000122132566, 20.458040962192968".'
        ),
        validators=[coordinates_validator,]
    )
    floor = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        verbose_name='этаж',
    )
    flat = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        verbose_name='квартира',
    )
    interfon = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        verbose_name='домофон'
    )

    class Meta:
        verbose_name = (_('My address'))
        verbose_name_plural = (_('My addresses'))

    def __str__(self):
        return f'Адрес {self.address}'

    def clean(self):
        super().clean()
        if self.base_profile.addresses.count() >= 3 and not self.pk:
            raise ValidationError("User can't have more than 3 addresses.")

    def save(self, *args, **kwargs):
        if self.address and (not self.coordinates):
            # Если есть адрес, но нет координат, извлекаем координаты из адреса
            try:
                lat, lon, status = (
                    google_validate_address_and_get_coordinates(self.address,
                                                                self.city))
                self.coordinates = f'{lat}, {lon}'
                self.point = Point(float(lon), float(lat))

            except ValidationError as e:
                logging.error((
                    'Ошибка при получении координат для адреса '
                    f'{self.address}: {e}'))

        elif self.coordinates:
            lat, lon = parce_coordinates(self.coordinates)
            self.coordinates = f'{lat}, {lon}'
            self.point = Point(float(lon), float(lat))
        else:
            # В противном случае, вызываем исключение или
            # выполняем другую логику по вашему усмотрению
            pass

        super().save(*args, **kwargs)


class BaseProfile(models.Model):
    ''' Базовая модель клиента, созданная для сведения клиентов сайта и ботов
    из соц сетей в одну сущность, которая будет хранить данные о клиенте:
    имя, фамилия, телефон, адрес, корзина, заказы и пр.'''

    web_account = models.OneToOneField(
        'WEBAccount',
        on_delete=models.PROTECT,
        related_name='base_profile',
        verbose_name='Аккаунт на сайте (web_account)',
        blank=True, null=True,
        help_text="Для изменения личных данных кликните на email."
        )
    messenger_account = models.OneToOneField(
        MessengerAccount,
        on_delete=models.SET_NULL,
        related_name='profile',
        verbose_name='Мессенджер',
        blank=True, null=True
        )
    first_name = models.CharField(
        'Имя',
        max_length=300,
        blank=True, null=True
        )
    last_name = models.CharField(
        'Фамилия',
        max_length=300,
        blank=True, null=True
        )
    phone = PhoneNumberField(
        verbose_name='телефон',
        unique=True,
        blank=True, null=True
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
    date_joined = models.DateTimeField(
        'Дата регистрации',
        auto_now_add=True
    )
    notes = models.CharField(
        'Пометки',
        max_length=1500,
        blank=True, null=True
    )
    date_of_birth = models.DateField(
        'День рождения',
        blank=True, null=True,
        validators=[validate_birthdate,],
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
        default=settings.DEFAULT_CREATE_LANGUAGE
    )
    orders_qty = models.PositiveSmallIntegerField(
        verbose_name='Кол-во заказов',
        help_text="Считается автоматически.",
        default=0,
        blank=True,
    )
    orders_amount = models.PositiveSmallIntegerField(
        verbose_name='Сумма заказов',
        help_text="Считается автоматически.",
        default=0,
        blank=True,
    )
    first_web_order = models.BooleanField(
        '1й зак на сайте',
        default=False
    )

    class Meta:
        # ordering = ['-id']
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')

    def __str__(self):
        return (
            f'{self.first_name}' if self.first_name is not None
            else f'Клиент id = {self.id}')

    def get_absolute_url(self):
        url = reverse(
            'admin:%s_%s_change' % (self._meta.app_label,
                                    self._meta.model_name),
            args=[self.pk])
        return url

    def get_orders_data(self):
        if hasattr(self, 'orders'):
            orders_aggregate = self.orders.aggregate(
                total_sum=Sum('final_amount_with_shipping'))
            total_sum = orders_aggregate.get('total_sum', 0) or 0
        else:
            total_sum = 0
        return f"{total_sum} rsd ({self.orders_qty} зак.)"

    @staticmethod
    def base_profile_update(instance):
        base_profile = BaseProfile.objects.filter(
                                    web_account=instance,
                                    )
        if base_profile:
            base_profile = base_profile[0]
            base_profile.web_account = instance
            base_profile.first_name = instance.first_name
            base_profile.last_name = instance.last_name
            base_profile.phone = instance.phone
            base_profile.email = instance.email
            base_profile.save(update_fields=[
                'web_account', 'first_name', 'last_name', 'phone',
                'email',
                ]
            )

    @staticmethod
    def base_profile_messegner_account_update(messenger, instance):
        if instance.base_profile.messenger_account:
            # если у юзера есть аккаунт

            if messenger == {} or messenger is None:
                # удалить привязку и аккаунт
                msngr_account = instance.base_profile.messenger_account
                instance.base_profile.messenger_account = None
                instance.base_profile.save(
                    update_fields=['messenger_account']
                )
                msngr_account.delete()

            else:
                # если у юзера есть мессенджер и МА уже существует,
                # то проверяем, есть ли у нового MA.profile.
                # Если есть:
                #     - скидываем юзернейм у MA
                #     - удяляем существующий МА у юзера
                #     - создаем новый MA с данными
                # Если нет:
                #     - привязываем МА к юзеру
                if isinstance(messenger, MessengerAccount):
                    if (hasattr(messenger, 'profile')
                        and
                        messenger.profile is not None
                        and
                        instance != messenger.profile):
                        # если владельцы НЕ совпадают, скидываем записи в старом аккаунте,
                        # создаем новый и привязываем его к юзеру
                        msngr_type = messenger.msngr_type
                        msngr_username = messenger.msngr_username
                        messenger.reset_telegram_account_info()

                        msngr_account = instance.base_profile.messenger_account
                        msngr_account.delete()

                        language = instance.web_language
                        messenger_acc_new = MessengerAccount.objects.create(
                            msngr_type=msngr_type,
                            msngr_username=msngr_username,
                            registered=True,
                            language=language
                        )
                        instance.base_profile.messenger_account = (
                            messenger_acc_new)
                        instance.base_profile.save(
                            update_fields=['messenger_account']
                        )

                    elif hasattr(messenger, 'profile') is False:
                        # если владельца МА нет, то привязываем его к юзеру
                        messenger.registered = True
                        messenger.save(update_fields=['registered'])

                        if hasattr(messenger, 'orders') and messenger.orders.exists():
                            order = messenger.orders.first()
                            order.transit_all_msngr_orders_to_base_profile(
                                instance.base_profile)

                        instance.base_profile.messenger_account = messenger
                        instance.base_profile.save(
                            update_fields=['messenger_account']
                            )

                else:
                    msngr_account = instance.base_profile.messenger_account
                    msngr_account.delete()

                    language = instance.web_language
                    messenger_acc_new = MessengerAccount.objects.create(
                        msngr_type=msngr_type,
                        msngr_username=msngr_username,
                        registered=True,
                        language=language
                    )
                    instance.base_profile.messenger_account = (
                        messenger_acc_new)
                    instance.base_profile.save(
                        update_fields=['messenger_account']
                    )

        else:
            # если у юзера НЕТ аккаунта
            if messenger:
                if isinstance(messenger, MessengerAccount):

                    if (hasattr(messenger, 'profile')
                        and
                        messenger.profile is not None
                        and
                        instance != messenger.profile):
                        # если владельцы НЕ совпадают, скидываем записи в старом аккаунте,
                        # создаем новый и привязываем его к юзеру
                        msngr_type = messenger.msngr_type,
                        msngr_username = messenger.msngr_username
                        messenger.reset_telegram_account_info()

                        language = instance.web_language
                        messenger_acc_new = MessengerAccount.objects.create(
                            msngr_type=msngr_type,
                            msngr_username=msngr_username,
                            registered=True,
                            language=language
                        )
                        instance.base_profile.messenger_account = (
                            messenger_acc_new)
                        instance.base_profile.save(
                            update_fields=['messenger_account']
                        )

                    elif hasattr(messenger, 'profile') is False:
                        # если владельца МА нет, то привязываем его к юзеру
                        messenger.registered = True
                        messenger.save(update_fields=['registered'])

                        if hasattr(messenger, 'orders') and messenger.orders.exists():
                            order = messenger.orders.first()
                            order.transit_all_msngr_orders_to_base_profile(
                                instance.base_profile)

                        instance.base_profile.messenger_account = messenger
                        instance.base_profile.save(
                            update_fields=['messenger_account']
                            )

                else:
                    language = instance.web_language
                    messenger_account = MessengerAccount.objects.create(
                        msngr_type=messenger.get('msngr_type'),
                        msngr_username=messenger.get('msngr_username'),
                        registered=True,
                        language=language
                    )
                    instance.base_profile.messenger_account = messenger_account
                    instance.base_profile.save(
                        update_fields=['messenger_account']
                        )

    def get_flag(self):
        if self.base_language == 'ru':
            flag = 'RU'
        elif self.base_language == 'en':
            flag = 'EN'
        else:
            flag = 'RS'
        return flag


class CustomWEBAccountManager(BaseUserManager):

    def _create_user(self, email, password=None, **extra_fields):
        """Create and save a User with the given email and password."""
        email = self.normalize_email(email)
        web_account = self.model(email=email, **extra_fields)
        web_account.full_clean()
        web_account.set_password(password)
        web_account.save()
        return web_account

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_active', False)
        extra_fields.setdefault('is_subscribed', True)
        extra_fields.setdefault('role', UserRoles.USER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', UserRoles.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        if extra_fields.get('is_active') is not True:
            raise ValueError('Superuser must have is_active=True.')
        if extra_fields.get('is_admin') is not True:
            raise ValueError('Superuser must have is_active=True.')

        return self._create_user(email, password, **extra_fields)


class WEBAccount(AbstractUser):
    ''' Модель для зарегистрированного пользователя сайта.
    Имеет привязку к базовому профилю,
    через который осуществляется пополнение корзины и сооздание заказов.

    При тестировании через shell не работали методы clean,
    а так же create_user. Для валидации созданы сигналы перед сохранением.
    '''
    username = None
    first_name = models.CharField(
        _('name'),
        max_length=150,
        validators=[validate_first_and_last_name,],
    )
    last_name = models.CharField(
        'last_name',
        max_length=150,
        validators=[validate_first_and_last_name,]
    )
    password = models.CharField(
        _('password'),
        max_length=100,
        validators=[MinLengthValidator(8)],
        null=True, blank=True
    )
    phone = PhoneNumberField(
        _('phone'),
        unique=True,
    )
    email = models.EmailField(
        'email',
        max_length=254,
        unique=True
    )
    city = models.CharField(
        max_length=40,
        verbose_name="город *",
        choices=settings.CITY_CHOICES,
        default=settings.DEFAULT_CITY,
        blank=True, null=True,
    )
    web_language = models.CharField(
        'Язык сайта',
        max_length=10,
        choices=settings.LANGUAGES,
        default=settings.DEFAULT_CREATE_LANGUAGE
    )
    notes = models.TextField(
        'Пометки',
        max_length=400,
        blank=True, null=True
    )
    # base_profile = models.OneToOneField(
    #     'BaseProfile',
    #     on_delete=models.PROTECT,
    #     verbose_name='базовый профиль',
    #     blank=True, null=True
    # )
    role = models.CharField(
        'Роль',
        max_length=9,
        choices=UserRoles.choices,
        default=UserRoles.USER
    )
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
    is_subscribed = models.BooleanField(
        'подписка',
        default=True,
        help_text='Подписка на рассылки.'
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.SET_NULL,
        related_name='admin',
        verbose_name='ресторан',
        blank=True, null=True
    )

    class Meta:
        # ordering = ['-date_joined']
        verbose_name = _('WEB account')
        verbose_name_plural = _('WEB accounts')

    def is_admin(self):
        return self.role == UserRoles.ADMIN or self.is_superuser

    def __str__(self):
        return f'{self.email}'

    def clean(self):
        super().clean()
        if not self.first_name:
            raise ValidationError({'first_name':
                                   _("First name can't be ampty.")})
        if not self.last_name:
            raise ValidationError({'last_name':
                                   _("Last name can't be ampty.")})
        if not self.email:
            raise ValidationError({'email': _("email can't be ampty.")})
        if not self.phone:
            raise ValidationError({'phone': _("Phone can't be ampty.")})

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if update_fields:
            if update_fields != ['last_login']:
                self.full_clean()

        super().save(*args, **kwargs)

    objects = CustomWEBAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone']


# ------    сигналы для создания base_profile при создании web account
@receiver(post_save, sender=WEBAccount)
def create_base_profile(sender, instance, created, **kwargs):
    if created:
        # если создается новый web_account
        if not (BaseProfile.objects.filter(web_account=instance).exists() and
                BaseProfile.objects.filter(phone=instance.phone).exists() and
                BaseProfile.objects.filter(email=instance.email).exists()):
            base_profile = BaseProfile(
                web_account=instance,
                first_name=instance.first_name,
                last_name=instance.last_name,
                phone=instance.phone,
                email=instance.email,
                base_language=instance.web_language
            )
        else:
            base_profile = BaseProfile.objects.filter(
                                    phone=instance.phone,
                                    )[0]
            base_profile.web_account = instance
        base_profile.save()
        # instance.base_profile = base_profile
        # instance.save(update_fields=['base_profile'])

    else:
        # если изменется существующий web_account
        BaseProfile.base_profile_update(instance)


def validate_phone_unique(value, user):
    if not value:
        raise ValidationError({"phone": "Please, provide the phone."},
                              code='invalid')
    if user.phone != value:
        if WEBAccount.objects.filter(phone=value).exists():
            raise ValidationError(
                {"phone": "WEB account with such phone already exists."},
                code='invalid')


def user_add_new_order_data(order):
    order.user.orders_qty += 1
    if order.is_first_order:
        order.user.first_web_order = True
    order.user.save(update_fields=['orders_qty', 'first_web_order'])
