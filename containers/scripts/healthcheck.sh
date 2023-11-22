#!/usr/bin/env bash

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && cd ../ && pwd )"

if [ -f "${PROJECT_DIR}/.env" ]; then
    # Load Environment Variables
    export $(grep -v '#' "${PROJECT_DIR}/.env" | sed 's/\r$//' | awk -F= '{print $1}' )
fi

CONTAINER_NAME=${1:-""}
CONTAINER_NAME="infodengue-${ENV:-dev}-${CONTAINER_NAME}"

echo "[II] Checking ${CONTAINER_NAME} ..."

while true; do
    HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null)
    if [ "${HEALTH_STATUS}" = "healthy" ]; then
        echo "[II] ${CONTAINER_NAME} is healthy."
        break
    else
        echo "[II] Waiting for ${CONTAINER_NAME} ..."
        sleep 5
    fi
done
