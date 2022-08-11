#!/bin/sh
set -e

# create registry container unless it already exists
reg_name='kind-registry'
reg_port='5000'
running="$(docker inspect -f '{{.State.Running}}' "${reg_name}" 2>/dev/null || true)"
if [ "${running}" != 'true' ]; then
  docker run \
    -d --restart=always -p "0.0.0.0:${reg_port}:5000" \
    --env=REGISTRY_STORAGE_DELETE_ENABLED=true \
    --name "${reg_name}" \
    registry:2
fi

# create network "kind" if doesn't exist
docker network inspect "kind" >/dev/null 2>&1 || \
    docker network create --driver bridge "kind"
# connect the registry to the cluster network
docker network connect "kind" "${reg_name}" || true
