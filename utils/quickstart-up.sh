#!/bin/bash
set -e

echo "Downloading Racetrack configuration files..."
mkdir -p lifecycle/tests/sample image_builder/tests/sample postgres
curl https://raw.githubusercontent.com/TheRacetrack/racetrack/master/utils/setup-registry.sh -sS -o setup-registry.sh
curl https://raw.githubusercontent.com/TheRacetrack/racetrack/master/docker-compose.yaml -sS -o docker-compose.yaml
curl https://raw.githubusercontent.com/TheRacetrack/racetrack/master/.env -sS -o .env
curl https://raw.githubusercontent.com/TheRacetrack/racetrack/master/utils/wait-for-lifecycle.sh -sS -o wait-for-lifecycle.sh
curl https://raw.githubusercontent.com/TheRacetrack/racetrack/master/lifecycle/tests/sample/compose.yaml -sS -o lifecycle/tests/sample/compose.yaml
curl https://raw.githubusercontent.com/TheRacetrack/racetrack/master/image_builder/tests/sample/compose.yaml -sS -o image_builder/tests/sample/compose.yaml
curl https://raw.githubusercontent.com/TheRacetrack/racetrack/master/postgres/init.sql -sS -o postgres/init.sql

echo "Setting up local Docker Registry..."
bash setup-registry.sh

DOCKER_GID=$((getent group docker || echo 'docker:x:0') | cut -d: -f3)
echo "Docker group ID: $DOCKER_GID"

echo "Setting up volumes..."
mkdir -p .plugins && chmod ugo+rw .plugins

echo "Starting containers..."
DOCKER_BUILDKIT=1 DOCKER_SCAN_SUGGEST=false DOCKER_GID=${DOCKER_GID} \
    docker compose up -d --no-build --pull=always

echo "Waiting until Racetrack is operational..."
LIFECYCLE_URL=http://localhost:7102 bash wait-for-lifecycle.sh

echo "Installing racetrack-client..."
pip3 install --upgrade racetrack-client

echo "Logging in to Racetrack with admin user..."
racetrack login http://localhost:7102 eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI

echo "Installing python3 job type in Racetrack..."
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type http://localhost:7102

echo "Preparing sample job to be deployed..."
mkdir -p sample && cd sample
cat << EOF > entrypoint.py
class Entrypoint:
def perform(self, a: float, b: float) -> float:
    """Add numbers"""
    return a + b
EOF

cat << EOF > fatman.yaml
name: adder
owner_email: sample@example.com
lang: python3
git:
remote: https://github.com/TheRacetrack/racetrack
python:
entrypoint_path: 'entrypoint.py'
entrypoint_class: 'Entrypoint'
EOF
