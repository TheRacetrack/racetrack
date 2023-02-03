#!/bin/bash
set -e
cd "$(dirname "$0")"

VERSION="${1:-2021-07-22}"
DOCKER_IMAGE_NAME="${DOCKER_IMAGE_NAME:-ghcr.io/theracetrack/racetrack/ci-test}"

DOCKER_BUILDKIT=1 docker build -t ${DOCKER_IMAGE_NAME}:${VERSION} -f ci-test.Dockerfile .

docker push ${DOCKER_IMAGE_NAME}:${VERSION}
