#!/bin/bash
# Docker Compose wrapper for hosts with only the Docker CLI (e.g. Jenkins-in-Docker).
# Tries: compose v2 plugin → docker-compose binary → compose sidecar container.

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
    return
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
    return
  fi

  local compose_image="${DOCKER_COMPOSE_IMAGE:-docker/compose:2.32.4}"
  local workdir
  workdir="$(pwd)"
  local -a run_args=(
    --rm
    -v /var/run/docker.sock:/var/run/docker.sock
    -v "${workdir}:${workdir}"
    -w "${workdir}"
  )

  if [ -f "${workdir}/.env" ]; then
    run_args+=(--env-file "${workdir}/.env")
  fi

  for key in POSTGRES_DOCKER_NETWORK DEPLOY_HOST DOCKER_BUILDKIT NEXT_PUBLIC_BUILD_ID \
    NEXT_PUBLIC_API_URL NEXT_PUBLIC_KC_URL NEXT_PUBLIC_KC_REALM NEXT_PUBLIC_KC_CLIENT_ID \
    INFRA_SERVICE_PORT; do
    if [ -n "${!key:-}" ]; then
      run_args+=(-e "${key}=${!key}")
    fi
  done

  if docker run --rm "$compose_image" version >/dev/null 2>&1; then
    docker run "${run_args[@]}" "$compose_image" "$@"
    return
  fi

  echo "ERROR: docker compose (plugin), docker-compose, or ${compose_image} not available" >&2
  exit 1
}
