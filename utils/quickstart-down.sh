#!/bin/bash
set -e

curl https://raw.githubusercontent.com/TheRacetrack/racetrack/master/utils/cleanup-fatmen-docker.sh -sS -o cleanup-fatmen-docker.sh
bash cleanup-fatmen-docker.sh
DOCKER_BUILDKIT=1 DOCKER_GID=0 \
    docker compose down
