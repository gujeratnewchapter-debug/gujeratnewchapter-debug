#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  python manage.py migrate --fake-initial --noinput
fi
python manage.py collectstatic --noinput
# Coolify provides $PORT; default to 8000 for local Docker.
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${GUNICORN_WORKERS:-1}" --access-logfile - --error-logfile -
