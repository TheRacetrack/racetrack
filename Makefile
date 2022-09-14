.PHONY: setup test clean registry

# docker tag of images
TAG ?= 2.2.1
DOCKER_REGISTRY ?= ghcr.io
DOCKER_REGISTRY_NAMESPACE ?= theracetrack/racetrack
DOCKER_GID=$(shell (getent group docker || echo 'docker:x:0') | cut -d: -f3 )

docker-compose = COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 DOCKER_SCAN_SUGGEST=false DOCKER_GID=${DOCKER_GID} \
	docker compose
docker = DOCKER_BUILDKIT=1 docker

-include .local.env

setup:
	python3 -m venv venv &&\
	. venv/bin/activate &&\
	pip install --upgrade pip setuptools &&\
	pip install -r requirements.txt &&\
	( cd racetrack_client && make setup ) &&\
	( cd racetrack_commons && make setup ) &&\
	( cd lifecycle && make setup ) &&\
	( cd image_builder && make setup ) &&\
	( cd dashboard && make setup ) &&\
	( cd wrappers/python_wrapper && make setup )
	@echo Activate your venv: . venv/bin/activate

setup-racetrack-client:
	python3 -m venv venv &&\
	. venv/bin/activate &&\
	pip install --upgrade pip setuptools &&\
	( cd racetrack_client && make setup )

setup-test-e2e:
	python3 -m venv venv &&\
	. venv/bin/activate &&\
	pip install -r tests/e2e/requirements.txt &&\
	( cd racetrack_client && make setup ) &&\
	( cd racetrack_commons && make setup )
	@echo Activate your venv: . venv/bin/activate

lint:
	-python -m mypy --ignore-missing-imports --exclude 'racetrack_client/build' racetrack_client
	-python -m mypy --ignore-missing-imports racetrack_commons
	-python -m mypy --ignore-missing-imports --exclude 'lifecycle/lifecycle/django/registry/migrations' lifecycle
	-python -m mypy --ignore-missing-imports image_builder
	-python -m mypy --ignore-missing-imports dashboard
	-python -m mypy --ignore-missing-imports wrappers/python_wrapper
	-python -m flake8 --ignore E501 --per-file-ignores="__init__.py:F401" \
		lifecycle image_builder dashboard wrappers/python_wrapper
	-python -m pylint --disable=R,C,W \
		lifecycle/lifecycle image_builder/image_builder dashboard/dashboard wrappers/python_wrapper/fatman_wrapper

format:
	python -m black -S --diff --color -l 120 \
		racetrack_client racetrack_commons lifecycle image_builder dashboard wrappers/python_wrapper

format-apply:
	python -m black -S -l 120 \
		racetrack_client racetrack_commons lifecycle image_builder dashboard wrappers/python_wrapper


test: compose-test

test-unit: test-python-wrapper test-racetrack-client test-lifecycle test-image-builder test-dashboard test-pub test-utils

test-python-wrapper:
	cd wrappers/python_wrapper && make test

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
	( cd tests/e2e && TEST_ENV=docker pytest -vv --tb=short -ra -s )

compose-test-e2e-auth:
	( cd tests/e2e && TEST_ENV=docker TEST_SUITE=auth pytest -vv --tb=short -ra -s  )

compose-test-e2e-full:
	( cd tests/e2e && TEST_ENV=docker TEST_SUITE=full pytest -vv --tb=short -ra -s  )

compose-test: test-unit compose-test-e2e

kind-test: test-unit kind-test-e2e


up: compose-up

down: compose-down

compose-run: registry docker-build local-registry-push-base
	$(docker-compose) up

compose-run-dev: registry docker-build local-registry-push-base
	$(docker-compose) --profile dev up

compose-run-stress: registry docker-build docker-build-stress local-registry-push-base
	$(docker-compose) -f docker-compose.yaml -f tests/stress/docker-compose.stress.yaml up

compose-up: registry docker-build local-registry-push-base
	$(docker-compose) up -d

compose-up-dev: registry docker-build local-registry-push-base
	$(docker-compose) --profile dev up -d

compose-up-service:
	$(docker-compose) build \
		--build-arg GIT_VERSION="`git describe --long --tags --dirty --always`" \
		--build-arg DOCKER_TAG="$(TAG)" \
		$(service)
	$(docker-compose) up -d $(service)
		
compose-up-docker-daemon: registry docker-build local-registry-push-base
	$(docker-compose) -f docker-compose.yaml \
		-f ./utils/docker-daemon/docker-compose.docker-daemon.yaml \
		--project-directory . \
		up -d

compose-down: docker-clean-fatman
	$(docker-compose) --profile dev down

compose-deploy-sample:
	LIFECYCLE_URL=http://localhost:7102 ./utils/wait-for-lifecycle.sh
	racetrack deploy sample/python-class/ http://localhost:7102 --force

compose-logs:
	$(docker-compose) logs -f

docker-build:
	$(docker-compose) build \
		--build-arg GIT_VERSION="`git describe --long --tags --dirty --always`" \
		--build-arg DOCKER_TAG="$(TAG)"
	@echo "Building base fatman images"
	$(docker) build -t racetrack/fatman-base/docker-http:latest -f wrappers/docker/docker-http/base.Dockerfile .
	$(docker) build -t racetrack/fatman-base/python3:latest -f wrappers/docker/python3/base.Dockerfile .

docker-build-stress:
	$(docker-compose) -f tests/stress/docker-compose.stress.yaml build

docker-push: docker-build
	docker login ${DOCKER_REGISTRY}

	docker tag racetrack/lifecycle:latest ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/lifecycle:$(TAG)
	docker push ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/lifecycle:$(TAG)
	docker tag racetrack/image-builder:latest ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/image-builder:$(TAG)
	docker push ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/image-builder:$(TAG)
	docker tag racetrack/dashboard:latest ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/dashboard:$(TAG)
	docker push ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/dashboard:$(TAG)
	docker tag racetrack/pub:latest ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/pub:$(TAG)
	docker push ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/pub:$(TAG)
	docker tag racetrack/pgbouncer:latest ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/pgbouncer:$(TAG)
	docker push ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/pgbouncer:$(TAG)
	
	docker tag racetrack/fatman-base/docker-http:latest ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/fatman-base/docker-http:$(TAG)
	docker push ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/fatman-base/docker-http:$(TAG)
	docker tag racetrack/fatman-base/python3:latest ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/fatman-base/python3:$(TAG)
	docker push ${DOCKER_REGISTRY}/${DOCKER_REGISTRY_NAMESPACE}/fatman-base/python3:$(TAG)

local-registry-push: docker-build local-registry-push-base
	docker tag racetrack/lifecycle:latest localhost:5000/racetrack/lifecycle:latest
	docker push localhost:5000/racetrack/lifecycle:latest
	docker tag racetrack/image-builder:latest localhost:5000/racetrack/image-builder:latest
	docker push localhost:5000/racetrack/image-builder:latest
	docker tag racetrack/dashboard:latest localhost:5000/racetrack/dashboard:latest
	docker push localhost:5000/racetrack/dashboard:latest
	docker tag racetrack/pub:latest localhost:5000/racetrack/pub:latest
	docker push localhost:5000/racetrack/pub:latest
	docker tag racetrack/pgbouncer:latest localhost:5000/racetrack/pgbouncer:latest
	docker push localhost:5000/racetrack/pgbouncer:latest

# push base fatman images to local registry
local-registry-push-base:
	docker tag racetrack/fatman-base/docker-http:latest localhost:5000/racetrack/fatman-base/docker-http:$(TAG)
	docker push localhost:5000/racetrack/fatman-base/docker-http:$(TAG)
	docker tag racetrack/fatman-base/python3:latest localhost:5000/racetrack/fatman-base/python3:$(TAG)
	docker push localhost:5000/racetrack/fatman-base/python3:$(TAG)

docker-clean-fatman:
	./utils/cleanup-fatmen-docker.sh

registry:
	./utils/setup-registry.sh

kind-cluster-up: registry
	kind create cluster --name racetrack --config utils/kind-config.yaml || true
	kind get clusters | grep -q 'racetrack' # make sure cluster exists
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

kind-deploy-sample:
	LIFECYCLE_URL=http://localhost:7002 ./utils/wait-for-lifecycle.sh
	racetrack deploy sample/python-class/ http://localhost:7002 --force

clean: compose-down kind-down

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
version-release-github: DOCKER_REGISTRY = ghcr.io
version-release-github: DOCKER_REGISTRY_NAMESPACE = theracetrack/racetrack
version-release-github: docker-push
	@echo "Racetrack version $(TAG) is released to registry ${DOCKER_REGISTRY}"

template-local-env:
	cp -n utils/.local.env.template .local.env
	@echo "Now fill in the .local.env file with your local settings"
