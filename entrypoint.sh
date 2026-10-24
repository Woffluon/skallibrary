#!/bin/sh
set -e

mkdir -p /app/media
python manage.py migrate --noinput

exec "$@"
