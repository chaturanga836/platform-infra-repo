# Jenkins Pipeline job — platform-infra-repo

Create this job on your Jenkins server to deploy infra-service co-located with etl-back.

## Job type

**Pipeline** (or Multibranch Pipeline if you want automatic branch discovery).

## Configuration

| Setting | Value |
|---------|-------|
| **Definition** | Pipeline script from SCM |
| **SCM** | Git |
| **Repository URL** | Your `platform-infra-repo` remote (e.g. `https://github.com/chaturanga836/platform-infra-repo.git`) |
| **Branch** | `*/master` |
| **Script Path** | `Jenkinsfile` |

## Agent requirements

The Jenkins agent (label `docker`) must have:

- Docker and Docker Compose v2
- Agent user in the `docker` group (`/var/run/docker.sock` access)
- Sibling repos checked out under the deploy root (default `/opt/elt`):

```
/opt/elt/
  etl-back/
  elt-frontend/
  platform-infra-repo/
  etl-deployment/
```

- `etl-deployment/.env` configured on the host (copy from `.env.example`)

Override paths via Jenkins job environment variables if needed:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEPLOY_ROOT` | `/opt/elt` | Parent directory containing sibling repos |
| `COMPOSE_PROFILE` | `backend` | Compose profile (`backend` or `full`) |
| `INFRA_SERVICE_PORT` | `9000` | Host port for health check |

## Pipeline stages

1. **Test** — runs on all branches: `pytest infra-service/tests`
2. **Deploy** — `master` only: runs [`deploy.sh`](../deploy.sh) (git pull + rebuild `infra-service`)
3. **Health** — `master` only: `curl http://127.0.0.1:9000/health`

## Optional: webhook trigger

Configure GitHub/GitLab webhook on push to `master` to trigger the pipeline automatically.

## Deploy ordering

| Scenario | Action |
|----------|--------|
| Fresh install | Run etl-deployment backend/full stack first |
| Infra code change | This Jenkins job only |
| `INTERNAL_SERVICE_TOKEN` change | Update `etl-deployment/.env`, redeploy `infra-service` **and** `api` |
| etl-back API change | Existing backend Jenkins job; no infra redeploy needed |

## Verification after first deploy

```bash
curl http://localhost:9000/health
docker ps | grep baas-infra-service
docker network ls | grep -E 'elt-net|data-plane-net'
```

Create a test workspace database via etl-back to confirm Docker socket provisioning works.
