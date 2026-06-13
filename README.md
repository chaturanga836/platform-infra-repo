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

## Production deploy (Jenkins / co-located with etl-back)

Infra-service runs on the **same host** as etl-back via [etl-deployment](https://github.com/chaturanga836/etl-deployment). All repos must be siblings:

```
/opt/elt/   (or your deploy root)
  etl-back/
  elt-frontend/
  platform-infra-repo/    ← this repo
  etl-deployment/         ← compose entry point
```

Configure [etl-deployment/.env](https://github.com/chaturanga836/etl-deployment) on the server (see `.env.example`). Infra-relevant variables:

| Variable | Purpose |
|----------|---------|
| `INTERNAL_SERVICE_TOKEN` | Shared secret with etl-back (`X-Internal-Token` header) |
| `PROVISION_MODE` | `docker` in production |
| `DATA_PLANE_NETWORK` | `data-plane-net` (created by etl-deployment compose) |
| `INFRA_SERVICE_PORT` | Host port (default `9000`) |
| `PLATFORM_INFRA_URL` | `http://infra-service:9000` (used by api container) |

**Manual deploy** (same steps as Jenkins):

```bash
bash deploy.sh
```

Or from etl-deployment:

```bash
docker compose --profile backend up -d --build infra-service
```

**Jenkins:** Pipeline job uses [`Jenkinsfile`](Jenkinsfile) — see [`jenkins/JOB.md`](jenkins/JOB.md) for job setup.

**Notes:**

- `INTERNAL_SERVICE_TOKEN` must match etl-back. If you change it, redeploy both `infra-service` and `api`.
- Redeploying infra-service does **not** destroy provisioned workspace databases — metadata persists in the `infra_instances` volume.
- Do **not** run `docker compose down -v` on etl-deployment — that destroys instance metadata and Postgres volumes.
- Host must have Docker socket access (`/var/run/docker.sock`) when `PROVISION_MODE=docker`.

