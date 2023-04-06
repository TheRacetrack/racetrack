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
	SITE_NAME=dev \
	python -u main.py

test:
	pytest -vv --tb=short -ra $(test)

setup-django-db:
	SECRET_KEY=dev DJANGO_DB_TYPE=sqlite ./init.sh


add-migration:
	python manage.py makemigrations dashboard &&\
	python manage.py migrate


front-setup:
	. ~/.nvm/nvm.sh &&\
	cd dashboard-front &&\
	nvm install v16.20.0 &&\
	nvm use v16.20.0 &&\
	npm install

npm-run: 
	. ./nvm-activate.sh &&\
	cd dashboard-front &&\
	npm run dev

npm-build:
	. ./nvm-activate.sh &&\
	cd dashboard-front &&\
	npm run build

build-in-docker:
	DOCKER_BUILDKIT=1 docker build -t frontend-builder:latest -f build.Dockerfile .

build-in-docker-replace: build-in-docker
	set -e ;\
	rm -rf ../static/react ;\
	ID=$$(docker create frontend-builder:latest) ;\
	echo $$ID ;\
	docker cp "$$ID:/build/build" ../static/react/ ;\
	docker rm -v $$ID ;\
