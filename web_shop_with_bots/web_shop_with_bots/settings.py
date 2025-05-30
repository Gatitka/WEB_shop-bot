# from pathlib import Path
import os
from datetime import timedelta
from django.utils.translation import gettext_lazy as _  # for translation
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from django.utils import timezone
from logging.handlers import TimedRotatingFileHandler


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGECT_DIR = os.path.dirname(os.path.dirname((BASE_DIR)))
load_dotenv(os.path.join(PROGECT_DIR,
                         'infra',
                         '.env'), verbose=True)

ENVIRONMENT = os.getenv('ENVIRONMENT')
DEVELOPER = os.getenv('DEVELOPER')

LOG_DIRECTORY = os.path.join(BASE_DIR, 'logging')
if not os.path.exists(LOG_DIRECTORY):
    os.makedirs(LOG_DIRECTORY)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {pathname} {funcName} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": os.getenv('CONSOLE_LOG_LEVEL', 'DEBUG'),
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            'level': os.getenv('FILE_LOG_LEVEL', 'DEBUG'),
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIRECTORY, 'yume.log'),
            'formatter': 'verbose',
            'encoding': 'utf-8',
            # 'mode': 'a',
            'when': 'midnight',
            # 'interval': 1,
            'backupCount': 10
        },
        "mail": {
            'level': 'ERROR',
            'class': 'logging.handlers.SMTPHandler',
            'mailhost': (os.getenv('EMAIL_HOST'), os.getenv('EMAIL_PORT')),
            'fromaddr': os.getenv('EMAIL_HOST_USER'),
            'toaddrs': ['gatitka@yandex.ru'],
            'subject': 'Django Error Log',
            'credentials': (os.getenv('EMAIL_HOST_USER'),
                            os.getenv('EMAIL_HOST_PASSWORD')),
            'secure': (),
        },
    },
    "loggers": {
        "api": {
            "handlers": [*(["console"] if os.getenv(
                            'ENABLE_CONSOLE_LOGGING',
                            'True') == 'True' else []),
                         *(["file"] if os.getenv(
                             'ENABLE_FILE_LOGGING',
                             'True') == 'True' else []),
                         *(["mail"] if os.getenv(
                             'ENABLE_MAIL_LOGGING',
                             'True') == 'True' else [])],
            "level": os.getenv('API_LOG_LEVEL'),
            "propagate": True,
        },
        "catalog": {
            "handlers": [*(["console"] if os.getenv(
                            'ENABLE_CONSOLE_LOGGING',
                            'True') == 'True' else []),
                         *(["file"] if os.getenv(
                             'ENABLE_FILE_LOGGING',
                             'True') == 'True' else []),
                         *(["mail"] if os.getenv(
                             'ENABLE_MAIL_LOGGING',
                             'True') == 'True' else [])],
            "level": os.getenv('CATALOG_LOG_LEVEL'),
            "propagate": True,
        },
        "delivery_contacts": {
            "handlers": [*(["console"] if os.getenv(
                            'ENABLE_CONSOLE_LOGGING',
                            'True') == 'True' else []),
                         *(["file"] if os.getenv(
                             'ENABLE_FILE_LOGGING',
                             'True') == 'True' else []),
                         *(["mail"] if os.getenv(
                             'ENABLE_MAIL_LOGGING',
                             'True') == 'True' else [])],
            "level": os.getenv('DELIVERY_LOG_LEVEL'),
            "propagate": True,
        },
        "promos": {
            "handlers": [*(["console"] if os.getenv(
                            'ENABLE_CONSOLE_LOGGING',
                            'True') == 'True' else []),
                         *(["file"] if os.getenv(
                             'ENABLE_FILE_LOGGING',
                             'True') == 'True' else []),
                         *(["mail"] if os.getenv(
                             'ENABLE_MAIL_LOGGING',
                             'True') == 'True' else [])],
            "level": os.getenv('PROMOS_LOG_LEVEL'),
            "propagate": True,
        },
        "shop": {
            "handlers": [*(["console"] if os.getenv(
                            'ENABLE_CONSOLE_LOGGING',
                            'True') == 'True' else []),
                         *(["file"] if os.getenv(
                             'ENABLE_FILE_LOGGING',
                             'True') == 'True' else []),
                         *(["mail"] if os.getenv(
                             'ENABLE_MAIL_LOGGING',
                             'True') == 'True' else [])],
            "level": os.getenv('SHOP_LOG_LEVEL'),
            "propagate": True,
        },
        "tm_bot": {
            "handlers": [*(["console"] if os.getenv(
                            'ENABLE_CONSOLE_LOGGING',
                            'True') == 'True' else []),
                         *(["file"] if os.getenv(
                             'ENABLE_FILE_LOGGING',
                             'True') == 'True' else []),
                         *(["mail"] if os.getenv(
                             'ENABLE_MAIL_LOGGING',
                             'True') == 'True' else [])],
            "level": os.getenv('TM_BOT_LOG_LEVEL'),
            "propagate": True,
        },
        "users": {
            "handlers": [*(["console"] if os.getenv(
                            'ENABLE_CONSOLE_LOGGING',
                            'True') == 'True' else []),
                         *(["file"] if os.getenv(
                             'ENABLE_FILE_LOGGING',
                             'True') == 'True' else []),
                         *(["mail"] if os.getenv(
                             'ENABLE_MAIL_LOGGING',
                             'True') == 'True' else [])],
            "level": os.getenv('USERS_LOG_LEVEL'),
            "propagate": True,
        },
        "cron": {
            "handlers": [*(["console"] if os.getenv(
                            'ENABLE_CONSOLE_LOGGING',
                            'True') == 'True' else []),
                         *(["file"] if os.getenv(
                             'ENABLE_FILE_LOGGING',
                             'True') == 'True' else []),
                         *(["mail"] if os.getenv(
                             'ENABLE_MAIL_LOGGING',
                             'True') == 'True' else [])],
            "level": os.getenv('CRON_LOG_LEVEL'),
            "propagate": True,
        },
        "web_shop_with_bots": {
            "handlers": [*(["console"] if os.getenv(
                            'ENABLE_CONSOLE_LOGGING',
                            'True') == 'True' else []),
                         *(["file"] if os.getenv(
                             'ENABLE_FILE_LOGGING',
                             'True') == 'True' else []),
                         *(["mail"] if os.getenv(
                             'ENABLE_MAIL_LOGGING',
                             'True') == 'True' else [])],
            "level": os.getenv('WSWB_LOG_LEVEL'),
            "propagate": True,
        },
    },
}

SECRET_KEY = os.getenv('SECRET_KEY')


DOCKER_COMPOSE_NAME = os.getenv('DOCKER_COMPOSE_NAME')

DEBUG = os.getenv('DEBUG') == 'True'
TEST_SERVER = os.getenv('TEST_SERVER')
SERVER = os.getenv('SERVER')

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

default_allowed_hosts = [
    'localhost',
    '127.0.0.1',
    '[::1]',
]

allowed_hosts = default_allowed_hosts.copy()
# Insert the TEST_SERVER and SERVER into the list if available
if TEST_SERVER or SERVER:
    if TEST_SERVER:
        allowed_hosts.append(str(TEST_SERVER))
    elif SERVER:
        allowed_hosts.append(str(SERVER))


if ENVIRONMENT in ['development', 'test_server']:
    allowed_hosts.append('testserver')   # для тестов
ALLOWED_HOSTS = allowed_hosts


default_installed_apps = [
    'catalog.apps.CatalogConfig',
    'shop.apps.ShopConfig',
    'users.apps.UsersConfig',
    'tm_bot.apps.TmBotConfig',
    'promos.apps.PromosConfig',
    'delivery_contacts.apps.DeliveryContactsConfig',
    'settings.apps.SettingsConfig',
    'audit.apps.AuditConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django_extensions',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'djoser',
    'corsheaders',
    'drf_yasg',
    'rest_framework.authtoken',
    'django_filters',
    'parler',   # language
    'django.contrib.gis',
    # 'django_celery_beat',
    'rangefilter',
    'django_summernote',
    'django_admin_inline_paginator',
    'debug_toolbar',
]
installed_apps = default_installed_apps.copy()
# Insert the TEST_SERVER and SERVER into the list if available
if SERVER:
    installed_apps.remove('debug_toolbar',)

INSTALLED_APPS = installed_apps


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'web_shop_with_bots.middlewares.AdminRULocaleMiddleware',
    # мидлвэр для отображения админки только на русском языке
    'web_shop_with_bots.middlewares.APIENLocaleMiddleware',
    # мидлвэр для перевода всех запросов на en для единства ответов ошибок
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'web_shop_with_bots.middlewares.AuditMiddleware',
    # мидлвэр для аудирования всех запросов к сайту
    # 'web_shop_with_bots.middlewares.APILoggingMiddleware',
    # мидлвэр для логирования всех запросов на к API

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',

]

ROOT_URLCONF = 'web_shop_with_bots.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates/')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'web_shop_with_bots.wsgi.application'

POSTGRES_DB = os.environ.get('POSTGRES_DB')
POSTGRES_USER = os.environ.get('POSTGRES_USER')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE'),
        'NAME': POSTGRES_DB,
        'USER': POSTGRES_USER,
        'PASSWORD': POSTGRES_PASSWORD,
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'users.validators.AlphanumericPasswordValidator',
    },
    {
        'NAME': 'users.validators.MaximumLengthValidator',
    },
]


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],

    'DATE_FORMAT': "%d.%m.%Y",

    'DATE_INPUT_FORMATS': [
        "%d.%m.%Y",
    ],

    'DATETIME_FORMAT': '%d.%m.%Y %H:%M',

    'DATETIME_INPUT_FORMATS': [
        '%d.%m.%Y %H:%M',
    ],

    'TIME_FORMAT': '%H:%M',

    'EXCEPTION_HANDLER': 'api.utils.utils.custom_exception_handler',
}

if DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
        'rest_framework.renderers.JSONRenderer',
    )

if ENVIRONMENT != 'development':
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
        'user': '10000/day', #  Лимит для UserRateThrottle
        'anon': '1000/day',  #  Лимит для AnonRateThrottle
    }
    REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle"
    ]


access_token_lifetime = os.getenv('ACCESS_TOKEN_LIFETIME')
refresh_token_lifetime = os.getenv('REFRESH_TOKEN_LIFETIME')

if access_token_lifetime is not None:
    ACCESS_TOKEN_LIFETIME = timedelta(seconds=int(access_token_lifetime))
else:
    ACCESS_TOKEN_LIFETIME = timedelta(seconds=480)

if refresh_token_lifetime is not None:
    REFRESH_TOKEN_LIFETIME = timedelta(seconds=int(refresh_token_lifetime))
else:
    REFRESH_TOKEN_LIFETIME = timedelta(seconds=7776000)

SIMPLE_JWT = {
    # Устанавливаем срок жизни токена
    'ACCESS_TOKEN_LIFETIME': ACCESS_TOKEN_LIFETIME,
    'REFRESH_TOKEN_LIFETIME': REFRESH_TOKEN_LIFETIME,
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),

    'BLACKLIST_AFTER_ROTATION': True,
}

TOKEN_MODEL = None
BLACKLIST_MODEL = 'yourapp.BlacklistedToken'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_PORT = os.getenv('EMAIL_PORT')

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER
EMAIL_ADMIN = EMAIL_HOST_USER

DOMAIN = os.getenv('DOMAIN')
PROTOCOL = os.getenv('PROTOCOL')
SITE_NAME = os.getenv('SITE_NAME')

DJOSER = {
    'LOGIN_FIELD': 'email',
    'SEND_ACTIVATION_EMAIL': True,
    'SEND_CONFIRMATION_EMAIL': True,
    'ACTIVATION_URL': 'activation/{uid}/{token}',

    'USERNAME_CHANGED_EMAIL_CONFIRMATION': True,

    'PASSWORD_RESET_CONFIRM_URL': 'reset_password_confirm/{uid}/{token}',
    'PASSWORD_RESET_SHOW_EMAIL_NOT_FOUND': True,
    'PASSWORD_CHANGED_EMAIL_CONFIRMATION': True,
    'LOGOUT_ON_PASSWORD_CHANGE': True,

    'SERIALIZERS': {
        'current_user': 'api.serializers.MyUserSerializer',
        'user_create': 'api.serializers.MyUserCreateSerializer',
        'password_reset_confirm': 'api.serializers.CustomPasswordResetConfirmSerializer',
        # проверка нового пароля при ресете по всем валидаторам пароля
    },
    'EMAIL': {
        'activation': 'api.utils.email.MyActivationEmail',
        'confirmation': 'api.utils.email.MyConfirmationEmail',
        'password_reset': 'api.utils.email.MyPasswordResetEmail',
        'password_changed_confirmation': 'api.utils.email.MyPasswordChangedConfirmationEmail',
        'username_changed_confirmation': 'api.utils.email.MyUsernameChangedConfirmationEmail',
    },
    'PERMISSIONS': {
        # 'user_delete': ['api.permissions.DenyAllPermission'],
        'username_reset': ['api.permissions.DenyAllPermission'],
        'username_reset_confirm': ['api.permissions.DenyAllPermission'],
        # запрет на удаление пользователей стандартным способом,
        # т.к. кастомный метод удаления, делая юзера неактивным
    },
}

# -------------------------------- Redis ----------------------------------


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv('REDIS_LOCATION', "redis://redis:6379/1")
        # "LOCATION": "redis://:redisadmin0@127.0.0.1:6379/1"  #local with pass
        # "LOCATION": "redis://:redisadmin0@redis:6379/1"    #test_server/production with pass
        # "LOCATION": "redis://redis:6379/1"  #backend container for frontend development
    }
}

# CELERY_BROKER_URL = 'redis://:redisadmin0@redis:6379/0'
# если применяется пароль к redis, то прописать и тут

PARLER_ENABLE_CACHING = False

CACHE_TIME = int(os.getenv('CACHE_TIME', 0))

# -------------------------------- DATETIME + OTHER ------------------------------------------

TIME_ZONE = 'Europe/Belgrade'

USE_TZ = True

DATE_FORMAT = "d.m.Y"
DATE_INPUT_FORMATS = ["%d.%m.%Y",]

DATETIME_FORMAT = "d.m.Y H:i"
DATETIME_INPUT_FORMATS = ["%d.%m.%Y %H:%i",]


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.WEBAccount'

FIRST_DAY_OF_WEEK = 1

# -------------------------------- STATIC + MEDIA ------------------------------------------

if ENVIRONMENT != 'development':
    STATIC_URL = f'{PROTOCOL}://{DOMAIN}/static/'
    MEDIA_URL = f'{PROTOCOL}://{DOMAIN}/media/'
else:
    STATIC_URL = '/static/'
    MEDIA_URL = '/media/'

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'my_static/'),]
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')



# -------------------------------- LANGUAGES ------------------------------------------

USE_L10N = False

# Включаем поддержку мультиязычности
USE_I18N = True

# Выбор языка по умолчанию
LANGUAGE_CODE = 'en'

# Список поддерживаемых языков
LANGUAGES = [
    ('en', _('English')),
    ('ru', _('Russian')),
    ('sr-latn', _('Serbian')),
    # Добавьте другие языки, если необходимо
]

PARLER_DEFAULT_LANGUAGE_CODE = 'sr-latn'
# By default, the fallback languages are the same as: [LANGUAGE_CODE]

PARLER_LANGUAGES = {
    None: (
        {'code': 'en', },
        {'code': 'ru', },
        {'code': 'sr-latn', },
    ),
    'default': {
        'fallbacks': ['sr-latn'],          # defaults to PARLER_DEFAULT_LANGUAGE_CODE
        'hide_untranslated': False,   # the default; let .active_translations() return fallbacks too.
    }
}

DEFAULT_CREATE_LANGUAGE = 'sr-latn'

LOCALE_PATHS = [
    os.path.join(BASE_DIR, "templates", "locale/"),
    os.path.join(BASE_DIR, "api", "locale/"),
    os.path.join(BASE_DIR, "tm_bot", "locale/"),
    os.path.join(BASE_DIR, "users", "locale/"),
    os.path.join(BASE_DIR, "venv_locale", "locale/"),
]

# -------------------------------- CORS ------------------------------------------

CORS_ORIGIN_ALLOW_ALL = True
# True Разрешает обрабатывать запросы с любого хоста, если False/удалить, то разрешены запросы только с этого хоста

# A list of origins that are authorized to make cross-site HTTP requests.
# The origins in this setting will be allowed, and the requesting origin
# will be echoed back to the client in the access-control-allow-origin header.

default_cors_allowed_origins = [
    f"{PROTOCOL}://localhost:3000",
    f"{PROTOCOL}://127.0.0.1",
]

cors_allowed_origins = default_cors_allowed_origins.copy()
# Insert the TEST_SERVER and SERVER into the list if available
if TEST_SERVER or SERVER:
    if TEST_SERVER:
        cors_allowed_origins.append(f"{PROTOCOL}://{TEST_SERVER}")
    elif SERVER:
        cors_allowed_origins.append(f"{PROTOCOL}://{SERVER}")
CORS_ALLOWED_ORIGINS = cors_allowed_origins

CORS_ALLOW_CREDENTIALS = True
# If True, cookies will be allowed to be included in cross-site HTTP requests.
# This sets the Access-Control-Allow-Credentials header in preflight and
# normal responses. Defaults to False.


# -------------------------------- CSRF --------------------------------------------

SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE'))
# срок годности кук для админа, чтобы не перелогиниваться в админке
# а так же срок CSRF-токена

if ENVIRONMENT != 'development':
    CSRF_COOKIE_SECURE = True  # Должно быть True, если используется HTTPS

CSRF_COOKIE_HTTPONLY = True
CSRF_USE_SESSIONS = True

default_csrf_trusted_origins = [
    f"{PROTOCOL}://localhost:3000",
    f"{PROTOCOL}://127.0.0.1",
]

csrf_trusted_origins = default_csrf_trusted_origins.copy()

# Insert the TEST_SERVER and SERVER into the list if available
if TEST_SERVER or SERVER:
    if TEST_SERVER:
        csrf_trusted_origins.append(str(f"{PROTOCOL}://{TEST_SERVER}"))
    elif SERVER:
        csrf_trusted_origins.append(str(f"{PROTOCOL}://{SERVER}"))
CSRF_TRUSTED_ORIGINS = csrf_trusted_origins

REST_USE_JWT = True

# -------------------------------- SECURITY --------------------------------------------

# Базовые настройки безопасности
if ENVIRONMENT != 'development':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# -------------------------------- DEBUG TOOL BAR --------------------------------------------

default_internal_ips = [
    '127.0.0.1',
]

internal_ips_origins = default_internal_ips.copy()

# Insert the TEST_SERVER and SERVER into the list if available
if TEST_SERVER:
    internal_ips_origins.append(str(TEST_SERVER))

INTERNAL_IPS = internal_ips_origins


# -------------------------------- GEOCODING --------------------------------------------

if ENVIRONMENT == 'development' and DEVELOPER == 'backend':

    GDAL_LIBRARY_PATH = r'C:\OSGeo4W\bin\gdal308.dll'
    GEOS_LIBRARY_PATH = r'C:\OSGeo4W\bin\geos_c.dll'

# -------------------------------- SENTRY MISTAKES INFORMATION----------------------------

if ENVIRONMENT in ['test_server', 'production']:
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
    )

# -------------------------------- TELEGRAM BOT  ----------------------------


ADMIN_BOT_TOKEN = os.getenv('ADMIN_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
BOTOBOT_API_KEY = os.getenv('BOTOBOT_API_KEY')
SEND_BOTOBOT_UPDATES = os.getenv('SEND_BOTOBOT_UPDATES')

# -------------------------------- BUSINESS LOGIC SETTINGS  ----------------------------

CITY_CHOICES = [
    ('Beograd', 'Beograd'),
    ('NoviSad', 'Novi Sad'),
]
DEFAULT_CITY = 'Beograd'
DEFAULT_RESTAURANT = 1

CREATED_BY = [
    (1, 'user'),
    (2, 'admin'),
]

DISCOUNT_TYPES = [
    (1, _('first_order')),
    (2, _('takeaway')),
    (3, _('cash_on_delivery')),
    (4, _('instagram_story')),
    (5, _('birthday')),
    (6, _('for insiders')),
]

DELIVERY_CHOICES = (
    ("delivery", "Доставка"),
    ("takeaway", "Самовывоз")
)

MAX_DISC_AMOUNT = 25

MESSENGERS = [
    ('tm', 'Telegram'),
    ('wts', 'WhatsApp'),
    ('vb', 'Viber'),
]

# List of order statuses
WAITING_CONFIRMATION = "WCO"
CONFIRMED = "CFD"
READY = "RDY"
ON_DELIVERY = "OND"
#DELIVERED = "DLD"
CANCELED = "CND"

ORDER_STATUS_CHOICES = (
    (WAITING_CONFIRMATION, "ожидает подтверждения"),
    (CONFIRMED, "подтвержден"),
    (READY, "готов"),
    (ON_DELIVERY, "отправлен"),
    #(DELIVERED, "выдан"),
    (CANCELED, "отменен")
)

ORDER_STATUS_TRANSLATIONS = {
    'WCO': {
        'ru': 'ожидает подтверждения',
        'en': 'waiting for confirmation',
        'sr-latn': 'čeka potvrdu'  # Пример перевода на сербскую латиницу
    },
    'CFD': {
        'ru': 'подтвержден',
        'en': 'confirmed',
        'sr-latn': 'potvrđen'
    },
    'RDY': {
        'ru': 'готов',
        'en': 'ready',
        'sr-latn': 'spreman'
    },
    'OND': {
        'ru': 'отправлен',
        'en': 'departured',
        'sr-latn': 'na isporuci'
    },
    # 'DLD': {
    #     'ru': 'доставлен',
    #     'en': 'delivered',
    #     'sr-latn': 'isporučen'
    # },
    'CND': {
        'ru': 'отменен',
        'en': 'canceled',
        'sr-latn': 'otkazan'
    }
}

PAYMENT_METHODS = [
    (None, '-------'),
    ('cash', 'cash'),
    ('card_on_delivery', 'bezgotovinsko'),
    ('card', 'card')
]

SOURCE_TYPES = [
    ('P1-1', 'Glovo'),
    ('P1-2', 'Wolt'),
    ('P2-1', 'Smoke'),
    ('P2-2', 'Не та дверь'),
    ('P3-1', 'Seal Tea'),
    ('1', 'внутренний'),
    # ('2', 'ресторан'),
    ('3', 'TM_Bot'),
    ('4', 'сайт'),
]

ORDER_TYPES = [
    ('P1-1', 'Glovo'),
    ('P1-2', 'Wolt'),
    ('P2-1', 'Smoke'),
    ('P2-2', 'Не та дверь'),
    ('P3-1', 'Seal Tea'),
    ('D', 'Доставка'),
    ('T', 'Самовывоз'),
]

PARTNERS_LIST = [
    'P1-1', 'P1-2', 'P2-1', 'P2-2', 'P3-1'
]

PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT = '2'
# из-за обращения к google api время обработки запроса дольше 1.48сек

# Увеличение этого времени может быть полезным, если ваш код содержит
# большое количество данных или выполнение сложных операций, которые
# требуют времени для обработки. Однако имейте в виду, что увеличение
# этого времени может привести к более долгому времени ожидания отладки
# в случае, если выражения должны быть вычислены во время отладки.




# -------------------------------- SUMMERNOTE  ----------------------------

SUMMERNOTE_CONFIG = {
    'iframe': False,  # Использовать iframe или нет
    'airMode': False,  # Режим редактирования по умолчанию (False = полный редактор)
    'toolbar': [
        ['style', ['style']],
        ['font', ['bold', 'underline', 'clear']],
        ['color', ['color']],
        ['para', ['ul', 'ol', 'paragraph']],
        # ['table', ['table']],
        ['insert', ['link']],        # 'picture', 'video']],
        ['view', ['fullscreen', 'codeview', 'help']],
    ],
    'summernote': {
        'width': '100%',
        'height': '180',
    },
    'attachment_require_authentication': True,  # Требовать аутентификацию для загрузки файлов
}
