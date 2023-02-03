.PHONY: setup run test

setup:
	pip install -r requirements.txt

run: setup-django-db
	DJANGO_DB_TYPE=sqlite DJANGO_DEBUG=True DJANGO_SETTINGS_MODULE="app.settings" \
	EXTERNAL_PUB_URL="http://localhost:7205/pub" \
	EXTERNAL_LIFECYCLE_URL="http://localhost:7202/lifecycle" \
	LIFECYCLE_URL="http://localhost:7202/lifecycle" \
	DEPLOYMENT_TYPE=localhost \
	AUTH_REQUIRED=false \
	SECRET_KEY=dev \
	LIFECYCLE_AUTH_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZWVkIjoiMjIzYThhM2ItNzBkOC00YzA4LWI4YmYtNzlkNDA3MDI3ZGE2Iiwic3ViamVjdCI6ImRhc2hib2FyZCIsInN1YmplY3RfdHlwZSI6ImludGVybmFsIiwic2NvcGVzIjpbImZ1bGxfYWNjZXNzIl19.CAww41hboBPHNflJxKBNRnO-Eo9Y_EKsfU66mK3kdk4 \
	SITE_NAME=dev \
	python -u main.py

# Run dashboard on localhost, connected to other services running on docker
run-local-rt-docker:
	DJANGO_DB_TYPE=sqlite DJANGO_DEBUG=True DJANGO_SETTINGS_MODULE="app.settings" \
	EXTERNAL_PUB_URL="http://localhost:7105/pub" \
	EXTERNAL_LIFECYCLE_URL="http://localhost:7102/lifecycle" \
	LIFECYCLE_URL="http://localhost:7102/lifecycle" \
	DEPLOYMENT_TYPE=localhost \
	AUTH_REQUIRED=true \
	SECRET_KEY=dev \
	LIFECYCLE_AUTH_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZWVkIjoiMjIzYThhM2ItNzBkOC00YzA4LWI4YmYtNzlkNDA3MDI3ZGE2Iiwic3ViamVjdCI6ImRhc2hib2FyZCIsInN1YmplY3RfdHlwZSI6ImludGVybmFsIiwic2NvcGVzIjpbImZ1bGxfYWNjZXNzIl19.CAww41hboBPHNflJxKBNRnO-Eo9Y_EKsfU66mK3kdk4 \
	SITE_NAME=dev \
	python -u main.py

test:
	pytest -vv --tb=short -ra $(test)

setup-django-db:
	SECRET_KEY=dev DJANGO_DB_TYPE=sqlite ./init.sh


add-migration:
	python manage.py makemigrations dashboard &&\
	python manage.py migrate
