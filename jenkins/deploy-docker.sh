#!/bin/bash
# Deploy from Jenkins when the workspace lives inside the Jenkins container.
# The host Docker daemon cannot bind-mount /var/jenkins_home/workspace paths
# (same constraint as jenkins/run-tests.sh).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE_CLI_IMAGE="${DOCKER_COMPOSE_CLI_IMAGE:-docker:27-cli}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-baas-platform}"
COMPOSE_FILE="stacks/platform/docker-compose.yml"
COMPOSE_PROFILE="backend"
VOL="platform-infra-jenkins-src-${BUILD_NUMBER:-0}-${RANDOM}"

cleanup_vol() {
  docker volume rm -f "$VOL" >/dev/null 2>&1 || true
}

compose_in_volume() {
  local -a env_args=(-e "COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}")
  for key in INTERNAL_SERVICE_TOKEN PROVISION_MODE DATA_PLANE_NETWORK \
    LOCAL_POSTGRES_URL INFRA_SERVICE_PORT; do
    if [ -n "${!key:-}" ]; then
      env_args+=(-e "${key}=${!key}")
    fi
  done

  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "${VOL}:/app" \
    -w /app \
    "${env_args[@]}" \
    "$COMPOSE_CLI_IMAGE" \
    sh -ec 'apk add --no-cache docker-cli-compose >/dev/null && exec docker compose "$@"' sh "$@"
}

echo "=== Creating deploy volume ${VOL} ==="
docker volume create "$VOL" >/dev/null
trap cleanup_vol EXIT

echo "=== Copying workspace into volume ==="
tar cf - \
  --exclude=.git \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='.venv' \
  --exclude='infra-service/.venv' \
  . | docker run --rm -i \
  -v "${VOL}:/out" \
  alpine sh -c 'rm -rf /out/* /out/.[!.]* 2>/dev/null || true; tar xf - -C /out'

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

echo "=== Ensuring Docker networks exist ==="
docker network create elt-net 2>/dev/null || true
docker network create data-plane-net 2>/dev/null || true

echo "=== Stopping previous compose stack ==="
compose_in_volume -f "$COMPOSE_FILE" --profile "$COMPOSE_PROFILE" down --remove-orphans 2>/dev/null \
  || compose_in_volume -f "$COMPOSE_FILE" --profile "$COMPOSE_PROFILE" down 2>/dev/null \
  || true

echo "=== Building and starting infra-service (compose) ==="
compose_in_volume -f "$COMPOSE_FILE" --profile "$COMPOSE_PROFILE" up -d --build --force-recreate

echo "=== Waiting for health ==="
for i in $(seq 1 24); do
  if curl -sf "http://127.0.0.1:${INFRA_SERVICE_PORT:-9000}/health"; then
    echo "Infra service OK"
    trap - EXIT
    cleanup_vol
    docker image prune -f
    exit 0
  fi
  if [ "$i" -eq 24 ]; then
    echo "ERROR: Infra service health check failed after compose up" >&2
    docker logs baas-infra-service --tail 80 2>/dev/null || true
    exit 1
  fi
  sleep 5
done
