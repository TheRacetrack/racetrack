.PHONY: setup test run

setup:
	pip install -r requirements.txt
	pip install -e .

test:
	cd tests &&\
	SECRET_KEY=dev AUTH_KEY=dev DJANGO_SETTINGS_MODULE="lifecycle.django.app.settings" \
	DB_TYPE=sqlite-memory DB_PATH=../lifecycle/django/db.sqlite3 \
	python -m pytest -vv --tb=short -ra $(test)

run:
	-docker network create racetrack_default
	DJANGO_DB_TYPE=sqlite DEPLOYMENT_TYPE=localhost \
	SECRET_KEY=dev CONFIG_FILE=tests/sample/local.yaml \
	AUTH_KEY=QaPU2UW8r7KXfRtLJVCKahCK93TKhVB5 \
	python -m lifecycle serve

recreate-django-db:
	cd lifecycle/django &&\
	rm -rf db.sqlite3 &&\
	python manage.py makemigrations registry &&\
	DJANGO_DB_TYPE=sqlite ./migrate.sh

recreate-django-migrations:
	cd lifecycle/django &&\
	rm -rf db.sqlite3 registry/migrations &&\
	python manage.py makemigrations registry &&\
	DJANGO_DB_TYPE=sqlite ./migrate.sh

add-migration:
	export DJANGO_DB_TYPE=sqlite SECRET_KEY=dev AUTH_KEY=QaPU2UW8r7KXfRtLJVCKahCK93TKhVB5 && cd lifecycle/django &&\
	python manage.py makemigrations registry &&\
	python manage.py migrate

init:
	cd lifecycle/django && SECRET_KEY=dev DJANGO_DB_TYPE=sqlite ./migrate.sh

# fill AUTH_KEY var with your secret key
generate-internal-tokens:
	python -m lifecycle generate-auth pub
	python -m lifecycle generate-auth dashboard
	python -m lifecycle generate-auth image-builder
