#!/bin/bash

until python lifecycle/django/manage.py migrate --check 2> /dev/null;
do
    echo "Waiting for Database migrations...";
    sleep 1;
done;
