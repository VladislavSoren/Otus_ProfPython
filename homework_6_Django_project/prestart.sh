#!/bin/bash

echo "Run migrations"
python manage.py migrate

echo "fill db prepared data"
python manage.py loaddata data.json

exec "$@"
