# from pathlib import Path
import os
from datetime import timedelta

from django.utils.translation import gettext_lazy as _  # for translation
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), 'infra', '.env'), verbose=True)

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
    'testserver',  # для тестов
]

allowed_hosts = default_allowed_hosts.copy()
# Insert the TEST_SERVER and SERVER into the list if available
if TEST_SERVER or SERVER:
    if TEST_SERVER:
        allowed_hosts.append(str(TEST_SERVER))
    if SERVER:
        allowed_hosts.append(str(SERVER))
print(allowed_hosts)
ALLOWED_HOSTS = allowed_hosts


INSTALLED_APPS = [
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
    # 'default': {
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': os.path.join(BASE_DIR, os.getenv('DB_FILE')),
    # }
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
]


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],

    'DATE_FORMAT': "%d-%m-%Y",

    'DATE_INPUT_FORMATS': [
        "%d.%m.%Y",
    ],

    'DATETIME_FORMAT': 'd.m.Y H:i',

    'DATETIME_INPUT_FORMATS': [
        '%d.%m.%Y %H:%i',
    ],
}


SIMPLE_JWT = {
    # Устанавливаем срок жизни токена
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=90),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

TOKEN_MODEL = None


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_PORT = os.getenv('EMAIL_PORT')

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER
EMAIL_ADMIN = EMAIL_HOST_USER

PROTOCOL = os.getenv('PROTOCOL')
DOMAIN = os.getenv('DOMAIN')

DJOSER = {
    'LOGIN_FIELD': 'email',
    'PASSWORD_CHANGED_EMAIL_CONFIRMATION': True,
    'SEND_ACTIVATION_EMAIL': True,
    'SEND_CONFIRMATION_EMAIL': True,
    'PASSWORD_RESET_CONFIRM_URL': 'api/v1/reset_password_confirm/{uid}/{token}',
    'ACTIVATION_URL': 'activation/{uid}/{token}',
    'SERIALIZERS': {
        'current_user': 'api.serializers.MyUserSerializer',
    },
    'EMAIL': {
        'activation': 'api.utils.CustomActivationEmail',
        'confirmation': 'djoser.email.ConfirmationEmail',
        'password_reset': 'djoser.email.PasswordResetEmail',
        'password_changed_confirmation': 'djoser.email.PasswordChangedConfirmationEmail',
    },
    'PERMISSIONS': {
        'user_delete': ['api.permissions.DenyAllPermission'],
        # запрет на удаление пользователей стандартным способом,
        # т.к. кастомный метод удаления, делая юзера неактивным
    },
}


TIME_ZONE = 'Europe/Belgrade'

USE_TZ = True

DATE_FORMAT = "d.m.Y"
DATE_INPUT_FORMATS = ["%d.%m.%Y",]

DATETIME_FORMAT = "d.m.Y H:i"
DATETIME_INPUT_FORMATS = ["%d.%m.%Y %H:%i",]


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.WEBAccount'

SESSION_COOKIE_AGE = 3600


STATIC_URL = 'static/'
# STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static/')]
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')


# -------------------------------- LANGUAGES ------------------------------------------

USE_L10N = False

# Включаем поддержку мультиязычности
USE_I18N = True

# Выбор языка по умолчанию
# LANGUAGE_CODE = 'en'
LANGUAGE_CODE = 'ru'

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

# -------------------------------- CORS ------------------------------------------

CORS_ORIGIN_ALLOW_ALL = True  # True Разрешает обрабатывать запросы с любого хоста, если False/удалить, то разрешены запросы только с этого хоста

# A list of origins that are authorized to make cross-site HTTP requests.
# The origins in this setting will be allowed, and the requesting origin
# will be echoed back to the client in the access-control-allow-origin header.

default_cors_allowed_origins = [
    f"{DOMAIN}://localhost",
    f"{DOMAIN}://127.0.0.1",
]

cors_allowed_origins = default_cors_allowed_origins.copy()
# Insert the TEST_SERVER and SERVER into the list if available
if TEST_SERVER or SERVER:
    if TEST_SERVER:
        cors_allowed_origins.append(f"{DOMAIN}://{TEST_SERVER}")
    if SERVER:
        cors_allowed_origins.append(f"{DOMAIN}://{SERVER}")
print(cors_allowed_origins)
CORS_ALLOWED_ORIGINS = cors_allowed_origins

CORS_ALLOW_CREDENTIALS = True
# If True, cookies will be allowed to be included in cross-site HTTP requests.
# This sets the Access-Control-Allow-Credentials header in preflight and
# normal responses. Defaults to False.


# CORS_URLS_REGEX = r'^/api/.*$' # шаблон адресов, к которым можно обращаться с других доменов


# -------------------------------- CSRF --------------------------------------------

# CSRF_COOKIE_SECURE = True  # Должно быть True, если используется HTTPS
# CSRF_COOKIE_HTTPONLY = True
CSRF_USE_SESSIONS = True

default_csrf_trusted_origins = [
    f"{DOMAIN}://localhost",
    f"{DOMAIN}://127.0.0.1",
]

csrf_trusted_origins = default_csrf_trusted_origins.copy()

# Insert the TEST_SERVER and SERVER into the list if available
if TEST_SERVER or SERVER:
    if TEST_SERVER:
        csrf_trusted_origins.append(str(f"{DOMAIN}://{TEST_SERVER}"))
    if SERVER:
        csrf_trusted_origins.append(str(f"{DOMAIN}://{SERVER}"))
print(csrf_trusted_origins)
CSRF_TRUSTED_ORIGINS = csrf_trusted_origins

REST_USE_JWT = True

# -------------------------------- DEBUG TOOL BAR --------------------------------------------

default_internal_ips = [
    '127.0.0.1',
]

internal_ips_origins = default_internal_ips.copy()

# Insert the TEST_SERVER and SERVER into the list if available
if TEST_SERVER or SERVER:
    if TEST_SERVER:
        internal_ips_origins.append(str(TEST_SERVER))
    if SERVER:
        internal_ips_origins.append(str(SERVER))
print(internal_ips_origins)
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

GDAL_LIBRARY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR))), 'Program Files', 'GDAL', 'gdal.dll')

GDAL_LIBRARY_PATH = r'C:\OSGeo4W\bin\gdal308.dll'
GEOS_LIBRARY_PATH = r'C:\OSGeo4W\bin\geos_c.dll'

# '/путь/к/библиотеке/GDAL.dll'
# if os.name == 'nt':
#     import platform
#     OSGEO4W = (r"C:\Users\gatit\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\OSGeo4W")
#     if '64' in platform.architecture()[0]:
#         OSGEO4W += "64"
#     assert os.path.isdir(OSGEO4W), "Directory does not exist: " + OSGEO4W
#     os.environ['OSGEO4W_ROOT'] = OSGEO4W
#     os.environ['GDAL_DATA'] = OSGEO4W + r"\share\gdal"
#     os.environ['PROJ_LIB'] = OSGEO4W + r"\share\proj"
#     os.environ['PATH'] = OSGEO4W + r"\bin;" + os.environ['PATH']


# -------------------------------- SENTRY MISTAKES INFORMATION----------------------------

# import sentry_sdk
# from sentry_sdk.integrations.django import DjangoIntegration

# sentry_sdk.init(
#    dsn=os.getenv('SENTRY_DSN'),
#    integrations=[DjangoIntegration()],
#)



CITY_CHOICES = [
    ('Белград', 'Белград'),
    ('Нови_Сад', 'Нови_Сад'),
]
