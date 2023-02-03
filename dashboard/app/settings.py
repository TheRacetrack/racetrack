import os
from pathlib import Path

from racetrack_commons.database.database import populate_database_settings

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def is_env_flag_enabled(flag_name: str, default: str) -> bool:
    return os.environ.get(flag_name, default).lower() in {'true', 't', 'yes', 'y', '1'}

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')
if SECRET_KEY == 'dev':
    print("Warning: secret key is in dev mode")
    # todo use logging

DEBUG = is_env_flag_enabled('DJANGO_DEBUG', 'true')

AUTH_REQUIRED = is_env_flag_enabled('AUTH_REQUIRED', 'true')
if not AUTH_REQUIRED:
    print("Warning: auth is disabled")

ALLOWED_HOSTS = ['*']

# Auth Token to call Lifecycle API
LIFECYCLE_AUTH_TOKEN = os.environ.get('LIFECYCLE_AUTH_TOKEN')

# Application definition

INSTALLED_APPS = [
    'dashboard.apps.DashboardConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'dashboard.middleware.UserCookieMiddleWare'
]

ROOT_URLCONF = 'app.urls'

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
                'dashboard.context_processors.racetrack_version_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'app.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DJANGO_DB_TYPE: str = os.environ.get('DJANGO_DB_TYPE', 'sqlite')

DATABASES = populate_database_settings(BASE_DIR)

DATABASE_ROUTERS = [
    'dashboard.database_routers.routers.Router',
]

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/dashboard/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sessions
# https://docs.djangoproject.com/en/3.2/ref/settings/#sessions

# This forces persistent sessions (so user's don't need to login every time they close browser)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Value in seconds; 290304000 is 10 years
SESSION_COOKIE_AGE = 290304000

SESSION_COOKIE_NAME = 'racetrack_sessionid'

LOGIN_URL = '/dashboard/accounts/login'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/dashboard/accounts/login'

RUNNING_ON_LOCALHOST = (DJANGO_DB_TYPE == 'sqlite')
