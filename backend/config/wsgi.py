"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# On Vercel (serverless), there is no separate worker to run
# `manage.py migrate`. Apply existing migrations at startup so the
# existing Supabase PostgreSQL schema stays in sync without any
# destructive operation (never flush/reset/drop).
# Only runs when VERCEL env is present (production runtime).
if os.environ.get('VERCEL'):
    try:
        import django

        django.setup()
        from django.core.management import call_command

        # --fake-initial is safe: if tables from 0001 already exist
        # (created outside Django), Django records 0001 as applied
        # without recreating tables, then applies later migrations
        # (0002-0005, e.g. subtitle) for real. Never drops/flushes.
        call_command('migrate', '--noinput', verbosity=1, fake_initial=True)
    except Exception:
        # Never block app startup; runtime logs will contain details.
        import traceback

        traceback.print_exc()

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
