#!/bin/sh
set -e

containers=$(docker ps --filter "label=racetrack-component=job" --format "{{.Names}}" -a)

if [ -z "$containers" ]; then
    exit 0
fi

echo "Removing Job containers: $containers"
docker rm -f $containers
