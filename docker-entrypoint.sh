#!/bin/sh
set -e

mkdir -p "${MEDIA_ROOT:-/app/media}"

echo "Running migrate..."
python manage.py migrate --noinput

echo "Running collectstatic..."
python manage.py collectstatic --noinput

echo "Starting application..."
exec "$@"
