#!/bin/sh
set -eu

# --fake-initial is safe: if initial tables already exist in the existing
# Supabase PostgreSQL (created outside Django), Django records them as
# applied without recreating tables, then applies later migrations for real.
# Never resets/drops/flushes data.
python manage.py migrate --fake-initial --noinput
python manage.py collectstatic --noinput
# Render provides $PORT (typically 10000); default to 8000 for local Docker.
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${GUNICORN_WORKERS:-3}" --access-logfile - --error-logfile -
