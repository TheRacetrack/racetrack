#!/bin/bash
set -e

# This should be run only in localhost mode, as in other modes the Lifecycle will init shared db

# change current directory to directory of this script
cd "$(dirname "$0")"

echo "Starting initing django..."

export DJANGO_SUPERUSER_USERNAME=admin
export DJANGO_SUPERUSER_PASSWORD=admin
export DJANGO_SUPERUSER_EMAIL=admin@admin.com
python manage.py migrate --database=${DJANGO_DB_TYPE} --no-input
# || true because second run will fail with "admin already exists" but it doesn't matter
python manage.py createsuperuser --no-input --database=${DJANGO_DB_TYPE} || true

echo "Done"
