from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=Csv())

CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv(), default='')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'accounts',
    'courses',
    'enrollments',
    'django_q',
    'integrations',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('POSTGRES_HOST'),
        'PORT': config('POSTGRES_PORT'),
        'CONN_MAX_AGE': 60,
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

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

AUTH_USER_MODEL = 'accounts.User'

# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'pt-BR'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Ninja JWT
NINJA_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# Storages
STORAGES = {
    'default': {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        'OPTIONS': {
            'endpoint_url': config('MINIO_ENDPOINT_URL'),
            'access_key': config('MINIO_ACCESS_KEY'),
            'secret_key': config('MINIO_SECRET_KEY'),
            'bucket_name': config('MINIO_BUCKET_NAME'),
            'default_acl': 'public-read',
            'querystring_auth': False,
            'file_overwrite': False,
        },
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# Django Q
Q_CLUSTER = {
    'name': 'area-membros',
    'workers': 2,
    'recycle': 500,
    'timeout': 60,
    'retry': 120,
    # Falha é final: dá ack na task que falhou e não reenfileira. Sem isso (default
    # ack_failures=False, max_attempts=0) uma task que sempre falha — ex.: SMTP fora —
    # é redelivered a cada `retry`s pra sempre, virando loop infinito que martela o
    # servidor de email. max_attempts=1 = sem retry automático.
    'ack_failures': True,
    'max_attempts': 1,
    'queue_limit': 50,
    'bulk': 10,
    'redis': {
        'host': config('REDIS_HOST', default='localhost'),
        'port': config('REDIS_PORT', default=6379, cast=int),
        'db': 0,
    },
}

PASSWORD_RESET_TIMEOUT = 60 * 60 * 24

# Frontend
FRONTEND_URL = config('FRONTEND_URL')

# Email
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Pacing dos emails de boas-vindas em massa (importação). Cada lote reusa 1 conexão
# SMTP e espaça os envios pra não disparar rajada de logins/volume que o provedor
# bloqueia. IMPORTANTE: EMAIL_BATCH_SIZE * EMAIL_PACE_SECONDS deve ficar abaixo do
# Q_CLUSTER['timeout'] (60s), senão o lote estoura o timeout do worker.
EMAIL_BATCH_SIZE = config('EMAIL_BATCH_SIZE', default=20, cast=int)
EMAIL_PACE_SECONDS = config('EMAIL_PACE_SECONDS', default=1.0, cast=float)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@localhost')

# Kiwify
KIWIFY_WEBHOOK_TOKEN = config('KIWIFY_WEBHOOK_TOKEN', default='')

# External Webhook
WEBHOOK_TOKEN = config('WEBHOOK_TOKEN', default='')
