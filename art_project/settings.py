# art_project/settings.py

import os  # ✅ Required for os.path.join
from pathlib import Path  # ✅ Required for BASE_DIR

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent  # ✅ This defines BASE_DIR

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key-here'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.postgres',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # ✅ Add this line
    'artist_logs',
    'debug_toolbar',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',  # ✅ Must be first
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'art_project.urls'

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

# ✅ REQUIRED: Static files configuration
STATIC_URL = '/static/'  # ✅ This was missing
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',  # ✅ PostgreSQL
        'NAME': 'apache_db',
        'USER': 'admin',
        'PASSWORD': 'admin',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Backup directory
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')  # ✅ Now works with BASE_DIR defined

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Debug Toolbar settings
# Debug Toolbar settings
INTERNAL_IPS = [
    '127.0.0.1',
    '::1',  # IPv6 localhost
]

# Authentication settings
LOGIN_REDIRECT_URL = '/prs-admin/'  # Where to redirect after login
LOGOUT_REDIRECT_URL = '/'           # Where to redirect after logout
LOGIN_URL = '/accounts/login/'     # Default login URL

# Authentication settings
LOGIN_REDIRECT_URL = '/prs-admin/'  # Redirect to prs-admin after login
LOGOUT_REDIRECT_URL = '/'          # Redirect to home after logout
LOGIN_URL = '/accounts/login/'    # Default login URL

# Template settings
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'artist_logs', 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # ✅ REQUIRED for authentication
                'django.contrib.auth.context_processors.auth',

                # ✅ REQUIRED for messages framework
                'django.contrib.messages.context_processors.messages',

                # Other common context processors
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.media',
                'django.template.context_processors.csrf',
                'django.template.context_processors.tz',
            ],
        },
    },
]