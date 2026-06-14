#!/bin/bash
# Run pytest inside Docker without bind-mounting the workspace.
# Required when Jenkins has no Python/pip on the agent (or runs in Docker where
# host workspace paths are not visible to the docker daemon).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}/infra-service"

if [ ! -f requirements.txt ]; then
  echo "ERROR: requirements.txt not found in ${ROOT}/infra-service"
  ls -la
  exit 1
fi

tar cf - \
  --exclude=.git \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='.venv' \
  . | docker run --rm -i -w /app python:3.12-slim bash -lc '
    set -e
    tar xf -
    pip install -q -r requirements.txt pytest
    PYTHONPATH=src pytest tests -q
  '
