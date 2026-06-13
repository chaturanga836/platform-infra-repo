#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

cd "$REPO_ROOT"
git fetch origin master
git reset --hard origin/master

docker network create elt-net 2>/dev/null || true
docker network create data-plane-net 2>/dev/null || true

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

docker compose -f stacks/platform/docker-compose.yml --profile backend up -d --build --force-recreate

curl -sf "http://127.0.0.1:${INFRA_SERVICE_PORT:-9000}/health"

docker image prune -f
