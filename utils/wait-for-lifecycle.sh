#!/bin/bash -e

# wait until response code is 200
while [[ "$(curl -s -o /dev/null -w ''%{http_code}'' ${LIFECYCLE_URL}/ready)" != "200" ]]; do
    echo "Waiting for Lifecycle to be ready...";
    sleep 1;
done
