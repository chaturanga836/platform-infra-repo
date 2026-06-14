#!/bin/bash
# Docker Compose wrapper for hosts with only the Docker CLI (e.g. Jenkins-in-Docker).
# Tries: compose v2 plugin → docker-compose binary → docker:cli sidecar with apk plugin.

COMPOSE_CLI_IMAGE="${DOCKER_COMPOSE_CLI_IMAGE:-docker:27-cli}"

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
    return
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
    return
  fi

  local workdir
  workdir="$(pwd)"
  local -a run_args=(
    --rm
    -v /var/run/docker.sock:/var/run/docker.sock
    -v "${workdir}:${workdir}"
    -w "${workdir}"
  )

  for key in POSTGRES_DOCKER_NETWORK DEPLOY_HOST DOCKER_BUILDKIT NEXT_PUBLIC_BUILD_ID \
    NEXT_PUBLIC_API_URL NEXT_PUBLIC_KC_URL NEXT_PUBLIC_KC_REALM NEXT_PUBLIC_KC_CLIENT_ID \
    INFRA_SERVICE_PORT COMPOSE_PROJECT_NAME; do
    if [ -n "${!key:-}" ]; then
      run_args+=(-e "${key}=${!key}")
    fi
  done

  docker run "${run_args[@]}" "$COMPOSE_CLI_IMAGE" \
    sh -ec 'apk add --no-cache docker-cli-compose >/dev/null && exec docker compose "$@"' sh "$@"
}
