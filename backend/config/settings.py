import os
from pathlib import Path

# Minimal Django settings for local development.
# Reads secrets from environment variables; do NOT store secrets here.

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-local-placeholder')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# If Vercel sets VERCEL_URL in the environment during build, allow it through
vercel_url = os.environ.get('VERCEL_URL')
if vercel_url:
    # strip scheme if present
    vercel_host = vercel_url.split('://')[-1].split('/')[0]
    if vercel_host and vercel_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(vercel_host)

INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # project apps (optional)
    'accounts',
    'ai_tutor',
    'certificates',
    'courses',
    'enrollments',
    'quizzes',
    'site_settings',
]

# If the project defines a custom user model, set it here
AUTH_USER_MODEL = os.environ.get('DJANGO_AUTH_USER_MODEL', 'accounts.User')

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # Keep SecurityMiddleware first, CorsMiddleware should come before CommonMiddleware
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'config.wsgi.application'

# Database: use sqlite for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DJANGO_DB_PATH', str(BASE_DIR / 'db.sqlite3')),
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (uploaded by users) - set explicitly to avoid empty MEDIA_URL
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# CORS configuration: allow the Next.js dev server to access the API
# Read from environment variable `DJANGO_CORS_ALLOWED_ORIGINS` (comma-separated),
# otherwise fall back to localhost dev origins. If `VERCEL_URL` is present,
# add it automatically as an allowed origin.
cors_env = os.environ.get('DJANGO_CORS_ALLOWED_ORIGINS')
if cors_env:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in cors_env.split(',') if o.strip()]
else:
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:3001',
        'http://127.0.0.1:3001',
        'http://localhost:3002',
        'http://127.0.0.1:3002',
    ]

if vercel_url:
    # Vercel provides VERCEL_URL without scheme (e.g. my-app.vercel.app)
    if vercel_url.startswith('http'):
        vercel_origin = vercel_url
    else:
        vercel_origin = f'https://{vercel_url}'
    if vercel_origin not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(vercel_origin)

# If you prefer to allow all origins in development, uncomment the line below
# CORS_ALLOW_ALL_ORIGINS = True

# In local development allow all origins when DEBUG to simplify frontend integration.
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Google OAuth client used by server-side verification of ID tokens in accounts.GoogleLoginView
GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')

# Django REST Framework settings: enable JWT and Supabase token authentication
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'accounts.authentication.SupabaseJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}
