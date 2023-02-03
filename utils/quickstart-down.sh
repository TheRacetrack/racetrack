#!/bin/bash
set -e

echo "Downloading configuration files..."
curl https://raw.githubusercontent.com/TheRacetrack/racetrack/master/docker-compose.yaml -sS -o docker-compose.yaml
curl https://raw.githubusercontent.com/TheRacetrack/racetrack/master/utils/cleanup-jobs-docker.sh -sS -o cleanup-jobs-docker.sh

echo "Shutting down Racetrack containers..."
bash cleanup-jobs-docker.sh
DOCKER_BUILDKIT=1 DOCKER_GID=0 \
    docker compose down

echo "Racetrack components are shut down."
