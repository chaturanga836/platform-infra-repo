#!/bin/bash
# Wait for baas-infra-service /health.
#
# Jenkins often runs inside Docker: curl to 127.0.0.1 hits the Jenkins container,
# not the host where compose publishes port 9000. Fall back to a host-network curl.

set -euo pipefail

HEALTH_PORT="${INFRA_SERVICE_PORT:-9000}"
HEALTH_URL="http://127.0.0.1:${HEALTH_PORT}/health"
CURL_IMAGE="${HEALTH_CURL_IMAGE:-curlimages/curl:8.5.0}"
MAX_ATTEMPTS="${HEALTH_MAX_ATTEMPTS:-24}"
SLEEP_SECS="${HEALTH_SLEEP_SECS:-5}"

check_infra_health() {
  local out=""
  if out="$(curl -sf "$HEALTH_URL" 2>/dev/null)"; then
    echo "$out"
    return 0
  fi
  if out="$(docker run --rm --network host "$CURL_IMAGE" -sf "$HEALTH_URL" 2>/dev/null)"; then
    echo "$out"
    return 0
  fi
  return 1
}

echo "=== Waiting for infra health (${HEALTH_URL}, host-network fallback) ==="
for i in $(seq 1 "$MAX_ATTEMPTS"); do
  if check_infra_health; then
    echo ""
    echo "Infra service OK"
    exit 0
  fi
  if [ "$i" -eq "$MAX_ATTEMPTS" ]; then
    echo "ERROR: Infra service health check failed" >&2
    docker logs baas-infra-service --tail 80 2>/dev/null || true
    exit 1
  fi
  echo "Health attempt ${i}/${MAX_ATTEMPTS} failed, retrying in ${SLEEP_SECS}s..."
  sleep "$SLEEP_SECS"
done
