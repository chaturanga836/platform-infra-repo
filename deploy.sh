#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

cd "$REPO_ROOT"

# shellcheck source=jenkins/compose.sh
source "${REPO_ROOT}/jenkins/compose.sh"

# Jenkins already checked out the commit; git fetch needs credentials in CI.
if [ -z "${BUILD_NUMBER:-}" ]; then
  git fetch origin master
  git reset --hard origin/master
fi

docker network create elt-net 2>/dev/null || true
docker network create data-plane-net 2>/dev/null || true

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

compose -f stacks/platform/docker-compose.yml --profile backend up -d --build --force-recreate

curl -sf "http://127.0.0.1:${INFRA_SERVICE_PORT:-9000}/health"

docker image prune -f
