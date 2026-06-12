# platform-infra-repo

BaaS platform infrastructure: service catalog, stack templates, and the **infra HTTP service** that provisions per-project databases (Docker containers or local dev fallback).

## Layout

```
platform-infra-repo/
  infra-service/     # FastAPI service (Docker + schema provisioning)
  catalog/           # Service metadata (postgres, centrifugo, …)
  stacks/
    project/         # Per-project templates (postgres container)
    platform/        # Platform compose snippet for infra-service
  data/instances/    # Runtime instance metadata (gitignored)
```

## Provision modes

| Mode | Behavior |
|------|----------|
| `local` | Dev fallback: logical instance per workspace on `LOCAL_POSTGRES_URL`; schemas for each database |
| `docker` | First database → new Postgres container; later databases → `CREATE SCHEMA` in same container |

## Run infra service locally

```bash
cd infra-service
pip install -r requirements.txt
set PYTHONPATH=src
set STACKS_PATH=../stacks
set PROVISION_MODE=local
uvicorn src.main:app --reload --port 9000
```

## API (internal)

```http
POST /internal/projects/{workspace_id}/databases
X-Internal-Token: changeme-internal-token

{
  "workspace_id": 42,
  "engine": "postgres",
  "database_name": "myapp",
  "existing_instance": null
}
```

## Docker (production demo)

```bash
docker network create data-plane-net 2>/dev/null || true
docker network create elt-net 2>/dev/null || true
docker compose -f stacks/platform/docker-compose.yml --profile backend up -d --build
```

Wire `etl-back` with `PLATFORM_INFRA_URL=http://localhost:9000`.
