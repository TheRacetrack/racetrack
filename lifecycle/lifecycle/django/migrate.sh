#!/bin/bash
set -e

# change current directory to directory of this script
cd "$(dirname "$0")"

echo "Migrating database..."

python manage.py migrate --database=${DJANGO_DB_TYPE} --no-input

echo "Migration completed."
