import importlib
import os

from django.test import TestCase


class HealthCheckTests(TestCase):
    def test_health_check_returns_ok(self):
        response = self.client.get('/health/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})


class FaviconRouteTests(TestCase):
    def test_favicon_svg_serves_asset(self):
        response = self.client.get('/favicon.svg')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')

    def test_favicon_ico_redirects_to_svg(self):
        response = self.client.get('/favicon.ico', follow=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/favicon.svg')


class StorageConfigFallbackTests(TestCase):
    def test_storage_defaults_to_filesystem_when_supabase_is_unconfigured(self):
        import config.settings as settings_module

        original = {
            'DJANGO_DEBUG': os.environ.get('DJANGO_DEBUG'),
            'DJANGO_SECRET_KEY': os.environ.get('DJANGO_SECRET_KEY'),
            'DJANGO_ALLOWED_HOSTS': os.environ.get('DJANGO_ALLOWED_HOSTS'),
            'DATABASE_URL': os.environ.get('DATABASE_URL'),
            'FRONTEND_BASE_URL': os.environ.get('FRONTEND_BASE_URL'),
            'EMAIL_HOST': os.environ.get('EMAIL_HOST'),
            'EMAIL_BACKEND': os.environ.get('EMAIL_BACKEND'),
            'SUPABASE_URL': os.environ.get('SUPABASE_URL'),
            'SUPABASE_JWKS_URL': os.environ.get('SUPABASE_JWKS_URL'),
            'SUPABASE_S3_ENDPOINT': os.environ.get('SUPABASE_S3_ENDPOINT'),
            'SUPABASE_S3_ACCESS_KEY_ID': os.environ.get('SUPABASE_S3_ACCESS_KEY_ID'),
            'SUPABASE_S3_SECRET_ACCESS_KEY': os.environ.get('SUPABASE_S3_SECRET_ACCESS_KEY'),
            'SUPABASE_STORAGE_BUCKET': os.environ.get('SUPABASE_STORAGE_BUCKET'),
            'SUPABASE_STORAGE_PUBLIC_URL': os.environ.get('SUPABASE_STORAGE_PUBLIC_URL'),
        }

        try:
            os.environ['DJANGO_DEBUG'] = 'False'
            os.environ['DJANGO_SECRET_KEY'] = 'test-secret'
            os.environ['DJANGO_ALLOWED_HOSTS'] = 'localhost'
            os.environ['DATABASE_URL'] = 'postgres://user:pass@localhost:5432/app'
            os.environ['FRONTEND_BASE_URL'] = 'https://example.com'
            os.environ['EMAIL_HOST'] = 'smtp.example.com'
            os.environ['EMAIL_BACKEND'] = 'django.core.mail.backends.smtp.EmailBackend'
            os.environ['SUPABASE_URL'] = 'https://example.supabase.co'
            os.environ['SUPABASE_JWKS_URL'] = 'https://example.supabase.co/auth/v1/jwks'
            for key in [
                'SUPABASE_S3_ENDPOINT',
                'SUPABASE_S3_ACCESS_KEY_ID',
                'SUPABASE_S3_SECRET_ACCESS_KEY',
                'SUPABASE_STORAGE_BUCKET',
                'SUPABASE_STORAGE_PUBLIC_URL',
            ]:
                os.environ.pop(key, None)

            reloaded = importlib.reload(settings_module)
            self.assertFalse(reloaded.SUPABASE_STORAGE_CONFIGURED)
            self.assertEqual(
                reloaded.STORAGES['default']['BACKEND'],
                'django.core.files.storage.FileSystemStorage',
            )
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            importlib.reload(settings_module)