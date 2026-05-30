#!/bin/sh
set -e

echo "Running migrate..."
python manage.py migrate --noinput

echo "Running collectstatic..."
python manage.py collectstatic --noinput

echo "Starting application..."
exec "$@"
