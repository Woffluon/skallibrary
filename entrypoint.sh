#!/bin/sh
set -e

mkdir -p /app/data /app/media
python manage.py migrate --noinput

exec "$@"
