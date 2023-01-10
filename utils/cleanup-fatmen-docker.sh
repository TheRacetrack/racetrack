#!/bin/sh
set -e

containers=$(docker ps --filter "label=racetrack-component=fatman" --format "{{.Names}}" -a)

if [ -z "$containers" ]; then
    exit 0
fi

echo "Removing Fatman containers: $containers"
docker rm -f $containers
