DOCKER_GID=$(shell (getent group docker || echo 'docker:x:0') | cut -d: -f3 )
docker-compose = COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 DOCKER_SCAN_SUGGEST=false DOCKER_GID=${DOCKER_GID} docker compose

up:
	$(docker-compose) up -d

down:
	$(docker-compose) down

# download "docker" client binary from https://download.docker.com/linux/static/stable/x86_64/docker-24.0.5.tgz
