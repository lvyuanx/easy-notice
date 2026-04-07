#!/bin/sh
set -e

if [ -n "${SQLITE_PATH}" ]; then
  mkdir -p "$(dirname "${SQLITE_PATH}")"
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-60}"
