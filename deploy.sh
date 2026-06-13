#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_ROOT="${DEPLOY_ROOT:-$(dirname "$REPO_ROOT")}"
COMPOSE_DIR="${COMPOSE_DIR:-$DEPLOY_ROOT/etl-deployment}"
COMPOSE_PROFILE="${COMPOSE_PROFILE:-backend}"

cd "$REPO_ROOT"
git fetch origin master
git reset --hard origin/master

cd "$COMPOSE_DIR"
docker compose --profile "$COMPOSE_PROFILE" up -d --build infra-service

curl -sf "http://127.0.0.1:${INFRA_SERVICE_PORT:-9000}/health"

docker image prune -f
