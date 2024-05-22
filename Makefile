.PHONY: setup test clean registry

# docker tag of images
TAG ?= 2.29.2
DOCKER_REGISTRY ?= ghcr.io
DOCKER_REGISTRY_NAMESPACE ?= theracetrack/racetrack
GHCR_PREFIX = ghcr.io/theracetrack/racetrack
DOCKER_GID=$(shell (getent group docker || echo 'docker:x:0') | cut -d: -f3 )

docker-compose = COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 DOCKER_SCAN_SUGGEST=false DOCKER_GID=${DOCKER_GID} \
	docker compose
docker = DOCKER_BUILDKIT=1 docker

# function: docker_tag_and_push,<src_image>,<target_image>
define docker_tag_and_push
	docker tag $(1) $(2)
	docker push $(2)
endef

-include .local.env

setup:
	python3 -m venv venv &&\
	. venv/bin/activate &&\
	pip install --upgrade pip setuptools &&\
	pip install -r requirements-test.txt -r requirements-dev.txt &&\
	( cd racetrack_client && make setup ) &&\
	( cd racetrack_commons && make setup ) &&\
	( cd lifecycle && make setup ) &&\
	( cd image_builder && make setup ) &&\
	( cd dashboard && make setup )
	@echo Activate your venv:
	@echo . venv/bin/activate

setup-racetrack-client:
	python3 -m venv venv &&\
	. venv/bin/activate &&\
	pip install --upgrade pip setuptools &&\
	( cd racetrack_client && make setup )

setup-test-unit:
	python3 -m venv venv &&\
	. venv/bin/activate &&\
	pip install -r requirements-test.txt &&\
	( cd racetrack_client && make setup ) &&\
	( cd racetrack_commons && make setup ) &&\
	( cd lifecycle && make setup ) &&\
	( cd image_builder && make setup ) &&\
	( cd dashboard && make setup )
	@echo Activate your venv: . venv/bin/activate

setup-test-e2e:
	python3 -m venv venv &&\
	. venv/bin/activate &&\
	pip install -r tests/e2e/requirements.txt &&\
	( cd racetrack_client && make setup ) &&\
	( cd racetrack_commons && make setup )
	@echo Activate your venv: . venv/bin/activate

install-racetrack-client:
	( cd racetrack_client && pip install -e . )

lint:
	-python -m mypy --ignore-missing-imports --exclude 'racetrack_client/build' racetrack_client
	-python -m mypy --ignore-missing-imports racetrack_commons
	-python -m mypy --ignore-missing-imports --exclude 'lifecycle/lifecycle/django/registry/migrations' lifecycle
	-python -m mypy --ignore-missing-imports image_builder
	-python -m mypy --ignore-missing-imports dashboard
	-python -m flake8 --ignore E501 --per-file-ignores="__init__.py:F401" \
		lifecycle image_builder dashboard
	-python -m pylint --disable=R,C,W \
		lifecycle/lifecycle image_builder/image_builder dashboard/dashboard

format:
	python -m black -S --diff --color -l 120 \
		racetrack_client racetrack_commons lifecycle image_builder dashboard

format-apply:
	python -m black -S -l 120 \
		racetrack_client racetrack_commons lifecycle image_builder dashboard


test: compose-test

test-unit: test-racetrack-client test-lifecycle test-image-builder test-dashboard test-pub test-utils

test-racetrack-client:
	cd racetrack_client && make test

test-lifecycle:
	cd lifecycle && make test

test-image-builder:
	cd image_builder && make test

test-dashboard:
	cd dashboard && make test

test-pub:
	cd pub && make test

test-pub-1: # Run single unit test of Pub
	cd pub && go test -v -run $(test) .

test-utils:
	cd utils && python -m pytest -v --tb=short -ra

test-e2e: compose-test-e2e

kind-test-e2e:
	( cd tests/e2e && pytest -vv --tb=short -ra -s )

kind-test-e2e-auth:
	( cd tests/e2e && TEST_SUITE=auth pytest -vv --tb=short -ra -s )

localhost-test-e2e-auth:
	( cd tests/e2e && TEST_ENV=localhost TEST_SUITE=auth pytest -vv --tb=short -ra -s )

compose-test-e2e:
	( cd tests/e2e && TEST_ENV=docker pytest -vv --tb=short -ra -s $(test))

compose-test-e2e-auth:
	( cd tests/e2e && TEST_ENV=docker TEST_SUITE=auth pytest -vv --tb=short -ra -s  )

compose-test-e2e-full:
	( cd tests/e2e && TEST_ENV=docker TEST_SUITE=full pytest -vv --tb=short -ra -s  )

compose-test: test-unit compose-test-e2e

kind-test: test-unit kind-test-e2e


up: compose-up

down: compose-down

compose-run: registry docker-build compose-volumes
	$(docker-compose) up

compose-run-dev: registry docker-build compose-volumes
	$(docker-compose) --profile dev up

compose-run-stress: registry docker-build docker-build-stress
	$(docker-compose) -f docker-compose.yaml -f tests/stress/docker-compose.stress.yaml up

compose-up: registry docker-build compose-volumes
	$(docker-compose) up -d

compose-up-dev: registry docker-build compose-volumes
	$(docker-compose) --profile dev up -d

compose-up-service: compose-volumes
	$(docker-compose) build \
		--build-arg GIT_VERSION="`git describe --long --tags --dirty --always`" \
		--build-arg DOCKER_TAG="$(TAG)" \
		$(service)
	$(docker-compose) up -d $(service)


compose-restart-service: compose-down-service compose-up-service

compose-down-service:
	$(docker-compose) down $(service)


up-pub:
	$(docker-compose) build \
		--build-arg GIT_VERSION="`git describe --long --tags --dirty --always`" \
		--build-arg DOCKER_TAG="$(TAG)" \
		pub
	$(docker-compose) up -d pub

# Start containers from pulled images (without building)
compose-up-pull: registry compose-volumes
	$(docker-compose) up -d --no-build --pull=always

compose-up-docker-daemon: registry docker-build compose-volumes
	$(docker-compose) -f docker-compose.yaml \
		-f ./utils/docker-daemon/docker-compose.docker-daemon.yaml \
		--project-directory . \
		up -d

compose-volumes:
	mkdir -p .plugins && chmod ugo+rw .plugins
	mkdir -p .plugins/metrics && chmod ugo+rw .plugins/metrics

compose-down: docker-clean-job
	$(docker-compose) --profile dev down
	rm -rf .plugins

compose-deploy-sample:
	LIFECYCLE_URL=http://127.0.0.1:7102 ./utils/wait-for-lifecycle.sh
	racetrack deploy sample/python-class/ --remote http://127.0.0.1:7102 --force

compose-logs:
	$(docker-compose) logs lifecycle lifecycle-supervisor image-builder dashboard pub -f

docker-build:
	$(docker-compose) build \
		--build-arg GIT_VERSION="`git describe --long --tags --dirty --always`" \
		--build-arg DOCKER_TAG="$(TAG)"

docker-build-stress:
	$(docker-compose) -f tests/stress/docker-compose.stress.yaml build

docker-push: docker-build
	docker login ${DOCKER_REGISTRY}
	$(call docker_tag_and_push,${GHCR_PREFIX}/lifecycle:latest,${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/lifecycle:${TAG})
	$(call docker_tag_and_push,${GHCR_PREFIX}/image-builder:latest,${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/image-builder:${TAG})
	$(call docker_tag_and_push,${GHCR_PREFIX}/dashboard:latest,${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/dashboard:${TAG})
	$(call docker_tag_and_push,${GHCR_PREFIX}/pub:latest,${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/pub:${TAG})
	$(call docker_tag_and_push,${GHCR_PREFIX}/pgbouncer:latest,${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/pgbouncer:${TAG})

docker-push-github: docker-build
	docker login ghcr.io
	docker push ${GHCR_PREFIX}/lifecycle:latest
	docker push ${GHCR_PREFIX}/image-builder:latest
	docker push ${GHCR_PREFIX}/dashboard:latest
	docker push ${GHCR_PREFIX}/pub:latest
	docker push ${GHCR_PREFIX}/pgbouncer:latest
	$(call docker_tag_and_push,${GHCR_PREFIX}/lifecycle:latest,${GHCR_PREFIX}/lifecycle:${TAG})
	$(call docker_tag_and_push,${GHCR_PREFIX}/image-builder:latest,${GHCR_PREFIX}/image-builder:${TAG})
	$(call docker_tag_and_push,${GHCR_PREFIX}/dashboard:latest,${GHCR_PREFIX}/dashboard:${TAG})
	$(call docker_tag_and_push,${GHCR_PREFIX}/pub:latest,${GHCR_PREFIX}/pub:${TAG})
	$(call docker_tag_and_push,${GHCR_PREFIX}/pgbouncer:latest,${GHCR_PREFIX}/pgbouncer:${TAG})

local-registry-push: docker-build
	$(call docker_tag_and_push,${GHCR_PREFIX}/lifecycle:latest,127.0.0.1:5000/racetrack/lifecycle:latest)
	$(call docker_tag_and_push,${GHCR_PREFIX}/image-builder:latest,127.0.0.1:5000/racetrack/image-builder:latest)
	$(call docker_tag_and_push,${GHCR_PREFIX}/dashboard:latest,127.0.0.1:5000/racetrack/dashboard:latest)
	$(call docker_tag_and_push,${GHCR_PREFIX}/pub:latest,127.0.0.1:5000/racetrack/pub:latest)
	$(call docker_tag_and_push,${GHCR_PREFIX}/pgbouncer:latest,127.0.0.1:5000/racetrack/pgbouncer:latest)

docker-clean-job:
	./utils/cleanup-jobs-docker.sh

registry:
	./utils/setup-registry.sh

registry-down:
	docker rm -f racetrack-registry || true

kind-cluster-up: registry
	kind create cluster --name racetrack --config utils/kind-config.yaml || true
	kind get clusters | grep -q 'racetrack' # make sure cluster exists
	kubectl config use-context kind-racetrack
	kubectl config set-context --current --namespace=racetrack
	kubectl cluster-info --context kind-racetrack
	# Enable service monitors in a cluster
	kubectl apply -f utils/servicemonitors.yaml

kind-deploy:
	kubectl apply -k kustomize/kind/ --context kind-racetrack

kind-up: kind-cluster-up local-registry-push kind-deploy

# Destroy kind cluster completely
kind-down:
	kind delete cluster --name racetrack

kind-redeploy: local-registry-push kind-deploy kind-delete-pods

kind-redeploy-force: kind-clear local-registry-push kind-clear-await kind-deploy

kind-restart: kind-down kind-up kind-delete-pods

# Clean all deployed resources from a kind, leaving empty kind cluster running
kind-clear:
	kubectl delete --wait=false --ignore-not-found=true -k kustomize/kind/ --context kind-racetrack

kind-clear-await:
	kubectl delete --wait=true --ignore-not-found=true -k kustomize/kind/ --context kind-racetrack

# Delete all pods (to redeploy new image versions)
kind-delete-pods:
	kubectl delete --wait=false --ignore-not-found=true pods -l app=racetrack

kind-logs:
	kubectl logs -l 'app in (racetrack)' --all-containers --prefix=true --tail=200 -f --max-log-requests 10

clean: compose-down kind-down registry-down

MR ?= 0
version-bump:
	./utils/version_bumper.py --mr $(MR)
version-bump-minor:
	./utils/version_bumper.py --part=minor
version-bump-major:
	./utils/version_bumper.py --part=major

# show current version
version-current:
	./utils/version_bumper.py --current

# First line is needed to reload newest TAG value
version-release: TAG = $(shell ./utils/version_bumper.py --current)
version-release: docker-push
	@echo "Racetrack version $(TAG) is released to registry ${DOCKER_REGISTRY}"

version-release-github: TAG = $(shell ./utils/version_bumper.py --current)
version-release-github: docker-push-github
	@echo "Racetrack version $(TAG) is released to registry ghcr.io"

template-local-env:
	cp -n utils/.local.env.template .local.env
	@echo "Now fill in the .local.env file with your local settings"

mkdocs-local:
	mkdocs serve

mkdocs-push:
	mkdocs gh-deploy --force --clean --verbose

install-plugins:
	racetrack plugin install github.com/TheRacetrack/plugin-docker-infrastructure
	racetrack plugin install github.com/TheRacetrack/plugin-python-job-type
