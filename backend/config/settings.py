import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

# Minimal Django settings for local development.
# Reads secrets from environment variables; do NOT store secrets here.

BASE_DIR = Path(__file__).resolve().parent.parent

# Local frontend auth settings provide the public Supabase project URL. In
# deployment, environment variables take precedence and should be configured
# directly by the hosting platform.
load_dotenv(BASE_DIR / '.env')
load_dotenv(BASE_DIR.parent / 'portal' / '.env.local')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true'

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError('DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false.')
    SECRET_KEY = 'django-insecure-local-development-only'

configured_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [host.strip() for host in configured_hosts.split(',') if host.strip()]
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
elif not DEBUG and not ALLOWED_HOSTS:
    raise RuntimeError('DJANGO_ALLOWED_HOSTS must be set when DJANGO_DEBUG is false.')

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
    'ess_platform',
]

# If the project defines a custom user model, set it here
AUTH_USER_MODEL = os.environ.get('DJANGO_AUTH_USER_MODEL', 'accounts.User')

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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

# SQLite remains the local default. Production can select PostgreSQL through
# deployment-time environment variables without storing credentials in code.
database_url = os.environ.get('DATABASE_URL', '')
database_url_parts = urlparse(database_url) if database_url else None
use_postgres = os.environ.get('DJANGO_DB_ENGINE', '').lower() == 'postgresql' or (
    database_url_parts and database_url_parts.scheme in ('postgres', 'postgresql')
)
if use_postgres:
    if database_url_parts and database_url_parts.scheme in ('postgres', 'postgresql'):
        database_config = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': database_url_parts.path.lstrip('/'),
            'USER': database_url_parts.username or '',
            'PASSWORD': database_url_parts.password or '',
            'HOST': database_url_parts.hostname or '',
            'PORT': str(database_url_parts.port or 5432),
        }
    else:
        database_config = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DJANGO_DB_NAME', ''),
            'USER': os.environ.get('DJANGO_DB_USER', ''),
            'PASSWORD': os.environ.get('DJANGO_DB_PASSWORD', ''),
            'HOST': os.environ.get('DJANGO_DB_HOST', ''),
            'PORT': os.environ.get('DJANGO_DB_PORT', '5432'),
        }
    DATABASES = {
        'default': {**database_config, 'CONN_MAX_AGE': int(os.environ.get('DJANGO_DB_CONN_MAX_AGE', '60'))}
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.environ.get('DJANGO_DB_PATH', str(BASE_DIR / 'db.sqlite3')),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = os.environ.get('DJANGO_STATIC_URL', '/static/')
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# User uploads use Supabase Storage in production so they survive Render
# restarts and redeployments. Local development keeps filesystem storage.
supabase_storage_values = {
    'endpoint_url': os.environ.get('SUPABASE_S3_ENDPOINT', ''),
    'access_key': os.environ.get('SUPABASE_S3_ACCESS_KEY_ID', ''),
    'secret_key': os.environ.get('SUPABASE_S3_SECRET_ACCESS_KEY', ''),
    'bucket_name': os.environ.get('SUPABASE_STORAGE_BUCKET', ''),
    'public_url': os.environ.get('SUPABASE_STORAGE_PUBLIC_URL', ''),
}
SUPABASE_STORAGE_CONFIGURED = all(supabase_storage_values.values())
if not DEBUG and not SUPABASE_STORAGE_CONFIGURED:
    raise RuntimeError(
        'Supabase Storage variables must be set when DJANGO_DEBUG is false.'
    )

STORAGES = {
    'default': {
        'BACKEND': (
            'storages.backends.s3.S3Storage'
            if SUPABASE_STORAGE_CONFIGURED
            else 'django.core.files.storage.FileSystemStorage'
        ),
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

if SUPABASE_STORAGE_CONFIGURED:
    AWS_S3_ENDPOINT_URL = supabase_storage_values['endpoint_url']
    AWS_ACCESS_KEY_ID = supabase_storage_values['access_key']
    AWS_SECRET_ACCESS_KEY = supabase_storage_values['secret_key']
    AWS_STORAGE_BUCKET_NAME = supabase_storage_values['bucket_name']
    AWS_S3_REGION_NAME = os.environ.get('SUPABASE_S3_REGION', 'us-east-1')
    AWS_S3_CUSTOM_DOMAIN = (
        supabase_storage_values['public_url']
        .removeprefix('https://')
        .removeprefix('http://')
        .rstrip('/')
    )
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_ADDRESSING_STYLE = 'path'
    AWS_S3_SIGNATURE_VERSION = 's3v4'

# Media files (uploaded by users) - set explicitly to avoid empty MEDIA_URL
MEDIA_URL = os.environ.get('DJANGO_MEDIA_URL', '/media/')
MEDIA_ROOT = Path(os.environ.get('DJANGO_MEDIA_ROOT', str(BASE_DIR / 'media')))

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

frontend_base_url = os.environ.get('FRONTEND_BASE_URL', '').rstrip('/')
if frontend_base_url and frontend_base_url not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(frontend_base_url)

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

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]
if frontend_base_url and frontend_base_url not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(frontend_base_url)

SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', str(not DEBUG)).lower() == 'true'
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '31536000' if not DEBUG else '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
if os.environ.get('DJANGO_SECURE_PROXY_SSL_HEADER', '').lower() == 'true':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Frontend base URL used by verification links and certificate URLs.
FRONTEND_BASE_URL = os.environ.get('FRONTEND_BASE_URL', 'http://localhost:3000')

# Supabase token verification. Prefer the explicit JWKS URL, but derive the
# standard endpoint when only the project URL is configured.
SUPABASE_URL = os.environ.get(
    'SUPABASE_URL',
    os.environ.get('NEXT_PUBLIC_SUPABASE_URL', ''),
).rstrip('/')
SUPABASE_ANON_KEY = os.environ.get(
    'SUPABASE_ANON_KEY',
    os.environ.get('NEXT_PUBLIC_SUPABASE_ANON_KEY', ''),
)
SUPABASE_JWT_SECRET = os.environ.get('SUPABASE_JWT_SECRET', '')
SUPABASE_JWKS_URL = os.environ.get(
    'SUPABASE_JWKS_URL',
    f'{SUPABASE_URL}/auth/v1/jwks' if SUPABASE_URL else '',
)

# Google OAuth client used by server-side verification of ID tokens in accounts.GoogleLoginView
GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')

# AI provider settings are optional; the tutor has a local fallback when no
# provider key is configured.
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
AI_MODEL = os.environ.get(
    'OPENROUTER_MODEL',
    os.environ.get('AI_MODEL', 'openai/gpt-4o-mini'),
)
OPENROUTER_BASE_URL = os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
AI_SITE_URL = os.environ.get('AI_SITE_URL', FRONTEND_BASE_URL)
AI_SITE_NAME = os.environ.get('AI_SITE_NAME', 'Ethiopian Startup School')

# Django REST Framework settings: enable JWT and Supabase token authentication
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'accounts.authentication.SupabaseJWTAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}

# Production logging: console output so Render/Gunicorn capture Django logs.
# No business logic affected.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {'format': '[{levelname}] {asctime} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'default'},
    },
    'root': {'handlers': ['console'], 'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO')},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
