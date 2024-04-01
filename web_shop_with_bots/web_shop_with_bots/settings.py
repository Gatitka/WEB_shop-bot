# from pathlib import Path
import os
from datetime import timedelta

from django.utils.translation import gettext_lazy as _  # for translation
from dotenv import load_dotenv

from users.validators import AlphanumericPasswordValidator

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(os.path.dirname(os.path.dirname((BASE_DIR))),
                         'infra',
                         '.env'), verbose=True)

ENVIRONMENT = os.getenv('ENVIRONMENT')
DEVELOPER = os.getenv('DEVELOPER')

if ENVIRONMENT == 'development' and DEVELOPER == 'backend':

    LOG_FILE_PATH = os.path.join(
        BASE_DIR, '/tmp', 'yume.log'
        ) if os.name != 'nt' else os.path.join(BASE_DIR, 'tmp', 'yume.log')

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
                "style": "{",
            },
        },
        "handlers": {
            "console": {
                "level": "WARNING",
                "class": "logging.StreamHandler",
            },
            "file": {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': LOG_FILE_PATH,
                'formatter': 'verbose',
                'encoding': 'utf-8',
            }
        },
        "loggers": {
            "django": {
                "handlers": ["console", "file"],
                "level": "DEBUG",
                "propagate": True,
            },
        },
    }

SECRET_KEY = os.getenv('SECRET_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')

DEBUG = os.getenv('DEBUG')
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
    if SERVER:
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
    'debug_toolbar',
    'django_summernote',   # HTML editable text in Admin section for promo
    'delivery_contacts.apps.DeliveryContactsConfig',
    'django_filters',
    'parler',   # language
    'django.contrib.gis'
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
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
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


DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('POSTGRES_DB', os.path.join(BASE_DIR, 'db.sqlite3')),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
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
    'EXCEPTION_HANDLER': 'api.utils.utils.custom_exception_handler'
}


SIMPLE_JWT = {
    # Устанавливаем срок жизни токена
    'ACCESS_TOKEN_LIFETIME': timedelta(seconds=int(os.getenv('ACCESS_TOKEN_LIFETIME'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(seconds=int(os.getenv('REFRESH_TOKEN_LIFETIME'))),
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
SITE_NAME = os.getenv('SITE_NAME')

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER
EMAIL_ADMIN = EMAIL_HOST_USER


PROTOCOL = os.getenv('PROTOCOL')
DOMAIN = os.getenv('DOMAIN')

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
        # 'user_create': 'api.serializers.MyUserSerializer'
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

TIME_ZONE = 'Europe/Oslo'

USE_TZ = True

DATE_FORMAT = "d.m.Y"
DATE_INPUT_FORMATS = ["%d.%m.%Y",]

DATETIME_FORMAT = "d.m.Y H:i"
DATETIME_INPUT_FORMATS = ["%d.%m.%Y %H:%i",]


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.WEBAccount'

SESSION_COOKIE_AGE = 60*60*24    # срок годности кук для админа, чтобы не перелогиниваться в админке


load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR))),
                         'sushi-frontend-rs',
                         '.env'), verbose=True)

STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'my_static/'),]
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

MEDIA_URL = '/media/'
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

PARLER_DEFAULT_LANGUAGE_CODE = 'ru'  # By default, the fallback languages are the same as: [LANGUAGE_CODE]
# PARLER_DEFAULT_LANGUAGE_CODE = 'en'

PARLER_LANGUAGES = {
    None: (
        {'code': 'en',},
        {'code': 'ru',},
        {'code': 'sr-latn',},
    ),
    'default': {
        'fallbacks': ['en'],          # defaults to PARLER_DEFAULT_LANGUAGE_CODE
        'hide_untranslated': False,   # the default; let .active_translations() return fallbacks too.
    }
}

LOCALE_PATHS = [
    os.path.join(BASE_DIR, "templates", "locale/"),
    os.path.join(BASE_DIR, "api", "locale/"),
    # os.path.join(BASE_DIR, "catalog", "locale/"),
    # os.path.join(BASE_DIR, "delivery_contacts", "locale/"),
    # os.path.join(BASE_DIR, "shop", "locale/"),
    os.path.join(BASE_DIR, "tm_bot", "locale/"),
    os.path.join(BASE_DIR, "users", "locale/"),
    os.path.join(BASE_DIR, "venv_locale", "locale/"),
    # os.path.join(BASE_DIR, "web_shop_with_bots", "locale/")
]

# -------------------------------- CORS ------------------------------------------

CORS_ORIGIN_ALLOW_ALL = True  # True Разрешает обрабатывать запросы с любого хоста, если False/удалить, то разрешены запросы только с этого хоста

# A list of origins that are authorized to make cross-site HTTP requests.
# The origins in this setting will be allowed, and the requesting origin
# will be echoed back to the client in the access-control-allow-origin header.

default_cors_allowed_origins = [
    f"{PROTOCOL}://localhost",
    f"{PROTOCOL}://127.0.0.1",
]

cors_allowed_origins = default_cors_allowed_origins.copy()
# Insert the TEST_SERVER and SERVER into the list if available
if TEST_SERVER or SERVER:
    if TEST_SERVER:
        cors_allowed_origins.append(f"{PROTOCOL}://{TEST_SERVER}")
    if SERVER:
        cors_allowed_origins.append(f"{PROTOCOL}://{SERVER}")
print(f'cors_allowed_origins: {cors_allowed_origins}')
CORS_ALLOWED_ORIGINS = cors_allowed_origins

CORS_ALLOW_CREDENTIALS = True
# If True, cookies will be allowed to be included in cross-site HTTP requests.
# This sets the Access-Control-Allow-Credentials header in preflight and
# normal responses. Defaults to False.


# CORS_URLS_REGEX = r'^/api/.*$' # шаблон адресов, к которым можно обращаться с других доменов


# -------------------------------- CSRF --------------------------------------------

if ENVIRONMENT != 'development':
    CSRF_COOKIE_SECURE = True  # Должно быть True, если используется HTTPS

CSRF_COOKIE_HTTPONLY = True
CSRF_USE_SESSIONS = True

default_csrf_trusted_origins = [
    f"{PROTOCOL}://localhost",
    f"{PROTOCOL}://127.0.0.1",
]

csrf_trusted_origins = default_csrf_trusted_origins.copy()

# Insert the TEST_SERVER and SERVER into the list if available
if TEST_SERVER or SERVER:
    if TEST_SERVER:
        csrf_trusted_origins.append(str(f"{PROTOCOL}://{TEST_SERVER}"))
    if SERVER:
        csrf_trusted_origins.append(str(f"{PROTOCOL}://{SERVER}"))
print(f'csrf_trusted_origins {csrf_trusted_origins}')
CSRF_TRUSTED_ORIGINS = csrf_trusted_origins

REST_USE_JWT = True

# -------------------------------- DEBUG TOOL BAR --------------------------------------------

default_internal_ips = [
    '127.0.0.1',
]

internal_ips_origins = default_internal_ips.copy()

# Insert the TEST_SERVER and SERVER into the list if available
if TEST_SERVER:
    internal_ips_origins.append(str(TEST_SERVER))

INTERNAL_IPS = internal_ips_origins


# -------------------------------- SUMMERNOTE --------------------------------------------
# settings for HTML text editing in admin
X_FRAME_OPTIONS = 'SAMEORIGIN'
SUMMERNOTE_CONFIG = {
    'iframe' : True,
    'summernote' : {
        'airMode': False,
        'width' : '100%',
        'lang' : 'ru-RU'
    },
    'disable_attachment': True,
    'toolbar': [
            ['style', ['style']],
            ['font', ['bold', 'underline', 'clear']],
            ['fontname', ['fontname']],
            ['color', ['color']],
            ['para', ['ul', 'ol', 'paragraph']],
            ['table', ['table']],
            ['insert', ['link']],
            ['view', ['fullscreen', 'codeview', 'help']],
        ],
    'width': '80%',
    'height': '200',
}

# -------------------------------- GEOCODING --------------------------------------------

if ENVIRONMENT == 'development' and DEVELOPER == 'backend':

    # GDAL_LIBRARY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR))), 'Program Files', 'GDAL', 'gdal.dll')

    GDAL_LIBRARY_PATH = r'C:\OSGeo4W\bin\gdal308.dll'
    GEOS_LIBRARY_PATH = r'C:\OSGeo4W\bin\geos_c.dll'

# -------------------------------- SENTRY MISTAKES INFORMATION----------------------------

# import sentry_sdk
# from sentry_sdk.integrations.django import DjangoIntegration

# sentry_sdk.init(
#    dsn=os.getenv('SENTRY_DSN'),
#    integrations=[DjangoIntegration()],
#)



CITY_CHOICES = [
    ('Beograd', 'Beograd'),
    ('Novi_sad', 'Novi Sad'),
]

DEFAULT_CITY = 'Beograd'
DEFAULT_RESTAURANT = 1
MAX_DISC_AMOUNT = 25


PAYMENT_METHODS = [
    ('cash', 'cash'),
    ('card', 'card'),
]

PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT = '2'
# из-за обращения к google api время обработки запроса дольше 1.48сек

# Увеличение этого времени может быть полезным, если ваш код содержит
# большое количество данных или выполнение сложных операций, которые
# требуют времени для обработки. Однако имейте в виду, что увеличение
# этого времени может привести к более долгому времени ожидания отладки
# в случае, если выражения должны быть вычислены во время отладки.
