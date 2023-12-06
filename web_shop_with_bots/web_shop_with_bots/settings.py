# from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), 'infra', '.env'), verbose=True)

SECRET_KEY = os.getenv('SECRET_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')


DEBUG = True

ALLOWED_HOSTS = []


INSTALLED_APPS = [
    'catalog.apps.CatalogConfig',
    'shop.apps.ShopConfig',
    'users.apps.UsersConfig',
    'tm_bot.apps.TmBotConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django_extensions',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'djoser',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'web_shop_with_bots.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, os.environ.get('DB_FILE')),
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
]


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],

    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}


SIMPLE_JWT = {
    # Устанавливаем срок жизни токена
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_PORT = os.getenv('EMAIL_PORT')

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER
EMAIL_ADMIN = EMAIL_HOST_USER

PROTOCOL = "http"
DOMAIN = "127.0.0.1:8000"
DJOSER = {
    'LOGIN_FIELD': 'email',
    'PASSWORD_CHANGED_EMAIL_CONFIRMATION': True,
    'SEND_ACTIVATION_EMAIL': True,
    'SEND_CONFIRMATION_EMAIL': True,
    'PASSWORD_RESET_CONFIRM_URL': 'api/v1/reset_password_confirm/{uid}/{token}',
    'ACTIVATION_URL': 'api/v1/auth/users/activation/{uid}/{token}',
    'SERIALIZERS': {},
    'EMAIL': {
        'activation': 'djoser.email.ActivationEmail',
        'confirmation': 'djoser.email.ConfirmationEmail',
        'password_reset': 'djoser.email.PasswordResetEmail',
        'password_changed_confirmation': 'djoser.email.PasswordChangedConfirmationEmail',
    },
}




SERIALIZERS: {
    # [...]
    # 'current_user': 'djoser.serializers.UserSerializer',
    'current_user': '',
    # [...]
}

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'Europe/Belgrade'

USE_I18N = True

USE_TZ = True




STATIC_URL = 'static/'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.WEBAccount'

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
]
CORS_ORIGIN_ALLOW_ALL = False  # True Разрешает обрабатывать запросы с любого хоста, если False/удалить, то разрешены запросы только с этого хоста
CORS_URLS_REGEX = r'^/api/.*$' # шаблон адресов, к которым можно обращаться с других доменов

SESSION_COOKIE_AGE = 3600

DATE_INPUT_FORMATS = ["%d.%m.%Y"]
USE_L10N = False

LANGUAGE_CHOICES = (
    ("EN", "English"),
    ("RUS", "Русский"),
    ("SRB", "Српски")
)

CURRENCY_CHOICES = (
    ("DIN", "Динар"),
    ("EURO", "Евро")
)
