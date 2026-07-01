from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.gis.db.models import PointField
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models, IntegrityError, transaction
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from django.conf import settings
from delivery_contacts.utils import (
    google_validate_address_and_get_coordinates,
    parce_coordinates, parse_address_comment)
from tm_bot.models import (MessengerAccount, OrdersBot, MessengerAccountBot)
from tm_bot.services import (check_new_account_subscription,
                             check_old_account_changed_subscription)
import logging
from users.validators import (validate_birthdate, validate_first_and_last_name,
                              coordinates_validator)

from delivery_contacts.models import Restaurant

from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError



logger = logging.getLogger(__name__)

AUTH_VIA = (('email', 'Email/Password'), ('telegram', 'Telegram'))


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
                lat, lon = (
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

        self.full_clean()
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
    def base_profile_messegner_account_link(base_profile, messenger_account):
        """
        Логика привязки/отвязки MessengerAccount к BaseProfile.

        messenger_account — dict вида:
        - {} / None                          -> отвязать
        - {"msngr_type": "tm", ...payload}   -> Telegram
        - {"msngr_type": "wts", "msngr_username": "+381..."} -> WhatsApp

        Здесь:
        - создаём/обновляем MessengerAccount,
        - проверяем, не привязан ли он к другому base_profile,
        - решаем, можно ли перепривязать или нужно выбросить ошибку.
        """
        base_profile = BaseProfile.objects.select_related('messenger_account').get(
            pk=base_profile.pk
        )
        # 1) Если Messenger account пустой

        if (
            messenger_account in ({}, None)
            or (
                isinstance(messenger_account, dict)
                and not messenger_account.get('msngr_type')
                and not messenger_account.get('msngr_username')
                )
        ):

            check_and_unlink_base_profile_from_ma(base_profile)
            return

        # 2) получаем или создаём объект MessengerAccount по словарю
        msngr_account = get_and_update_or_create(messenger_account,
                                                 base_profile)
        current_ma = base_profile.messenger_account

        # 2.1) у base_profile НЕТ привязанного MA
        if not current_ma:
            logger.debug('Base_profile %s has no MA linked.', base_profile)
            if not getattr(msngr_account, 'profile', None):
                # MA свободен → просто привязываем
                link_ma_to_base_profile(base_profile, msngr_account,
                                        messenger_account)

            else:
                # MA уже привязан к какому-то base_profile
                if msngr_account.registered is False:
                    # MA не "закреплён" за живым сайтом-акком →
                    # можно оторвать и привязать
                    unlink_ma_from_base_profile(msngr_account)
                    link_ma_to_base_profile(base_profile, msngr_account,
                                            messenger_account)
                else:
                    # Зареганный (живой) чужой акк →
                    # просим сперва отвязать через владельца
                    raise DRFValidationError(
                        {"messenger_account": ("First unlink the new "
                                               "Messenger Account from "
                                               "the previous profile.")}
                    )
            return

        # 3) у base_profile УЖЕ есть MessengerAccount
        logger.debug('\nBase_profile %s has MA linked.', base_profile)

        if current_ma == msngr_account:
            # Ничего не меняем — уже привязан этот же аккаунт
            return

        # 3.1) хотим привязать другой MA
        if not getattr(msngr_account, 'profile', None):
            # Новый MA никому не принадлежит →
            # отвязываем старый у base_profile и ставим новый
            check_and_unlink_base_profile_from_ma(base_profile)
            link_ma_to_base_profile(base_profile, msngr_account,
                                    messenger_account)

        else:
            # Новый MA уже к кому-то привязан
            if msngr_account.registered is False:
                # бот-аккаунт, привязанный к "пустышке" →
                # можно оторвать и перекинуть
                check_and_unlink_base_profile_from_ma(base_profile)
                unlink_ma_from_base_profile(msngr_account)
                link_ma_to_base_profile(base_profile, msngr_account,
                                        messenger_account)
            else:
                # реальный зарегистрированный чужой MA
                raise DRFValidationError(
                    {"messenger_account": ("First unlink the new "
                                           "Messenger Account from "
                                           "the previous profile.")}
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
        unique=True, blank=True, null=True
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
    auth_via = models.CharField(max_length=16, choices=AUTH_VIA, default='email')

    @property
    def is_dummy_telegram(self):
        return (
            self.auth_via == 'telegram'
            and bool(self.email)
            and self.email.endswith('@example.invalid')
        )

    class Meta:
        # ordering = ['-date_joined']
        verbose_name = _('WEB account')
        verbose_name_plural = _('WEB accounts')

    def is_admin(self):
        return self.role == UserRoles.ADMIN or self.is_superuser

    def __str__(self):
        return f'{self.email}'

    # def clean_fields(self, exclude=None):
    #     try:
    #         super().clean_fields(exclude=exclude)
    #         print(1)
    #     except ValidationError as e:
    #         # Обычных пользователей валидируем как и раньше
    #         if not self.is_dummy_telegram:
    #             raise

    #         error_dict = getattr(e, 'error_dict', None)
    #         if not error_dict:
    #             raise

    #         # Для dummy Telegram разрешаем невалидные/пустые first_name/last_name
    #         error_dict.pop('first_name', None)
    #         error_dict.pop('last_name', None)

    #         if error_dict:
    #             raise ValidationError(error_dict)

    def clean(self):
        super().clean()

        if not self.email:
            raise ValidationError({'email': _("email can't be empty.")})

        if not self.is_dummy_telegram:
            if not self.first_name:
                raise ValidationError({'first_name': _("First name can't be empty.")})
            if not self.last_name:
                raise ValidationError({'last_name': _("Last name can't be empty.")})
            if not self.phone:
                raise ValidationError({'phone': _("Phone can't be empty.")})

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()

        if "@example.invalid" not in self.email:
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
    order.user.first_web_order = True
    order.user.save(update_fields=['orders_qty', 'first_web_order'])


def user_add_name_and_phone(order):
    """ Обновить имя пользователя и телефон, если заказ из TM.
        Если имя base_profile.first_name совпадает с messenger_account.msngr_name,
        то меняем продублированный юзернейм у base_profile   """
    try:
        with transaction.atomic():

            order_user = order.user

            if order_user.first_name in ['', order.msngr_account.msngr_first_name]:
                order_user.first_name = order.recipient_name

            if order_user.phone is None and order.recipient_phone:
                order_user.phone = order.recipient_phone

            if (order.delivery.type == "delivery"
                    and order.delivery_zone.name != 'уточнить'):
                # если это заказ доставки и адрес и зона определились верно, без ошибок
                get_or_create_user_address_safe(order_user, order)

            order_user.save(update_fields=['first_name', 'phone'])

    except IntegrityError as e:
        # если телефон занят — пробуем сохранить без него
        if 'users_baseprofile_phone_key' in str(e):
            try:
                order_user.phone = None
                order_user.save(update_fields=['first_name'])
            except Exception:
                logger.exception("Profile update failed after phone conflict")
        else:
            logger.exception("Unexpected integrity error in user_add_name_and_phone")


def check_and_unlink_base_profile_from_ma(base_profile):
    """
    Если у base_profile есть messenger_account:
      - отвязываем его от base_profile
      - сбрасываем ссылку profile у MA
      - ставим registered=False
    """
    logger.debug(
        "Unlinking start: arg.bp.pk=%s, arg.bp.messenger_account_id=%s",
        base_profile.pk,
        base_profile.messenger_account_id,
    )
    # принудительно перечитаем профиль из БД
    # так 100% возьмется актуальная версия base_profile и отвяжет привязку
    fresh_bp = BaseProfile.objects.select_related(
        'messenger_account').get(pk=base_profile.pk)

    logger.debug(
        "Unlinking DB state: fresh.bp.pk=%s, fresh.bp.messenger_account_id=%s",
        fresh_bp.pk,
        fresh_bp.messenger_account_id,
    )
    ma = fresh_bp.messenger_account
    if not ma:
        logger.debug("Base profile has no MA linked.")
        return

    base_profile.messenger_account = None
    base_profile.save(update_fields=['messenger_account'])

    old_tm_base_profile = BaseProfile.objects.select_related(
                            "web_account"
                                ).filter(
                            web_account__email__contains=f"tg_{ma.msngr_id}@example.invalid"
                                ).first()

    if old_tm_base_profile is not None:
        old_tm_base_profile.messenger_account = ma
        old_tm_base_profile.save(update_fields=["messenger_account"])
    ma.registered = False
    ma.subscription = False
    ma.save(update_fields=['registered', 'subscription'])
    logger.debug("\nUnlinking BP from MA finished. Base_profile || Messenger_account: "
                 f"{base_profile} + {base_profile.messenger_account}")


def unlink_ma_from_base_profile(msngr_account: MessengerAccount):
    """
    Отвязывает MessengerAccount от его текущего base_profile (если есть).
    Цель: получить MA без привязок.
    """
    logger.debug("\nUnlinking MA from BP started. \nMessenger_account: %s",
                 msngr_account)
    bp = getattr(msngr_account, 'profile', None)
    if bp and bp.messenger_account == msngr_account:
        bp.messenger_account = None
        bp.save(update_fields=['messenger_account'])

    msngr_account.registered = False
    msngr_account.subscription = False
    msngr_account.save(update_fields=['registered', 'subscription'])
    logger.debug("\nUnlinking MA from BP ended."
                 "\nEX_base_profile.messenger_account: %s"
                 "\nmessenger_account.registered: %s",
                 bp.messenger_account, msngr_account)


def get_and_update_or_create(data, base_profile):
    """
    По dict'у messenger_account находим или создаём MessengerAccount.
    Обновляем:
      - username / phone
      - first_name / last_name
      - city (из payload, приоритетный)
      - subscription (разрешение писать)
    """
    logger.debug("\n\nMA get/update/create started. \nData: %s\nBase_profile: %s",
                 data, base_profile)
    msngr_type = data.get('msngr_type')

    # Подготовим общие штуки
    # приоритет — из payload
    city = data.get('city') or getattr(base_profile, 'city', None)
    language = getattr(base_profile, 'base_language', settings.DEFAULT_CREATE_LANGUAGE)

    # --- TELEGRAM ---
    if msngr_type == 'tm':
        telegram_id = data.get('id') or data.get('msngr_id')
        telegram_id = str(telegram_id)
        username = data.get('username') or data.get('msngr_username') or ""
        first_name = data.get('first_name') or data.get('msngr_first_name') or ""
        last_name = data.get('last_name') or data.get('msngr_last_name') or ""
        subscription = data.get('subscription')

        defaults = {
            'msngr_username': username,
            'msngr_first_name': first_name,
            'msngr_last_name': last_name,
            'language': language,
            'city': city,
            'subscription': subscription,
        }

        ma, created = MessengerAccount.objects.get_or_create(
            msngr_type='tm',
            msngr_id=telegram_id,
            defaults=defaults
        )
        logger.debug("\n\nMA, created. %s, %s.", ma, created)

        if created is False:
            changed = False

            if username and ma.msngr_username != username:
                ma.msngr_username = username
                changed = True
            if first_name and ma.msngr_first_name != first_name:
                ma.msngr_first_name = first_name
                changed = True
            if last_name and ma.msngr_last_name != last_name:
                ma.msngr_last_name = last_name
                changed = True
            if city and ma.city != city:
                ma.city = city
                changed = True
            if subscription is not None and ma.subscription != bool(subscription):
                ma.subscription = bool(subscription)
                changed = True

            if changed:
                ma.save()
                if city:
                    bot = OrdersBot.objects.filter(city=city, is_active=True).first()
                    if bot:
                        MessengerAccountBot.objects.filter(
                            messenger_account=ma,
                            bot=bot,
                        ).update(
                            last_login=timezone.now(),
                            tg_can_write=True,
                        )
                check_old_account_changed_subscription(ma)

        else:
            if city:
                ma.create_bot_links(city)
            check_new_account_subscription(ma)
            # ma.save()

        return ma

    # --- WHATSAPP ---
    if msngr_type == 'wts':
        phone = data.get('msngr_username')
        subscription = data.get('subscription')

        ma, created = MessengerAccount.objects.get_or_create(
            msngr_type='wts',
            msngr_username=phone,
            defaults={
                'msngr_phone': phone,
                'language': language,
                'city': city,
                'subscription': subscription,
            }
        )
        if created is False:
            changed = False
            if city and ma.city != city:
                ma.city = city
                changed = True
            if subscription is not None and ma.subscription != bool(subscription):
                ma.subscription = bool(subscription)
                changed = True

            if changed:
                ma.save()

        return ma


def link_ma_to_base_profile(base_profile, msngr_account, ma_data):
    """
    Привязка MA к base_profile:
      - ставим связь в обе стороны,
      - помечаем registered=True,
      - переносим заказы с MA на base_profile (если есть).
    """
    logger.debug("\nLink MA to BP started.\nBase profile: %s"
                 "\nMessenger account: %s\nMA data: %s",
                 base_profile, msngr_account, ma_data)

    old_ma = base_profile.messenger_account

    if old_ma and old_ma != msngr_account:
        old_ma.registered = False
        old_ma.subscription = False
        old_ma.save(update_fields=['registered', 'subscription'])

    base_profile.messenger_account = msngr_account
    base_profile.save(update_fields=['messenger_account'])

    msngr_account.registered = True
    msngr_account.subscription = ma_data['subscription']
    msngr_account.save(update_fields=['registered', 'subscription'])

    logger.debug("\nMA and BP linked.\n"
                 "\nBase profile.messenger_account = %s",
                 base_profile.messenger_account)

    # Перенос заказов, как у тебя уже реализовано в ордерах
    if hasattr(msngr_account, 'orders') and msngr_account.orders.exists():
        order = msngr_account.orders.first()
        if hasattr(order, 'transit_all_msngr_orders_to_base_profile'):
            order.transit_all_msngr_orders_to_base_profile(base_profile)
            logger.debug("Existing MA orders were transited to BP.")

    from tm_bot.tasks import send_link_confirmation_message
    send_link_confirmation_message.delay(msngr_account.id, msngr_account.city)


def get_or_create_dummy_webacount_and_baseprofile(msngr, tg):
    # web_account create + base_profile

    from django.contrib.auth import get_user_model
    User = get_user_model()

    raw_first_name = tg.get('first_name') or ""
    raw_last_name = tg.get('last_name') or ""

    # хелпер для “очищенных” имён
    def safe_validate(value):
        try:
            validate_first_and_last_name(value)
            return value
        except ValidationError:
            return ""

    clean_first_name = safe_validate(raw_first_name)
    clean_last_name = safe_validate(raw_last_name)

    user, created = User.objects.get_or_create(
        email=f"tg_{str(tg['id'])}@example.invalid",
        defaults=dict(
            first_name=clean_first_name,
            last_name=clean_last_name,
            auth_via="telegram",
            is_active=True,
            is_subscribed=True,
            web_language='ru'
        )
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])

    # есть сигнал, который создает base_profile при создании web_account
    base_profile = user.base_profile
    base_profile.messenger_account = msngr
    base_profile.save(update_fields=["messenger_account"])
    # msngr.registered остается False, msngr.registered остается True

    return user


def get_or_create_user_address_safe(base_profile, order):
    city = order.city
    address = order.recipient_address
    qs = UserAddress.objects.filter(
        base_profile=base_profile,
        city=city,
        address=address,
    ).order_by('id')

    obj = qs.first()
    if obj:
        return obj

    # если не нашли — создаём
    address_parts = parse_address_comment(order.address_comment)
    defaults = {
            "coordinates": order.coordinates,
            **address_parts,
        },
    return UserAddress.objects.create(
        base_profile=base_profile,
        city=city,
        address=address,
        **defaults
    )
