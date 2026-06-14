# Jenkins Pipeline job — platform-infra-repo

Deploy infra-service on the same host as etl-back using this repo's compose file.

## Job type

**Pipeline** (or Multibranch Pipeline).

## Configuration

| Setting | Value |
|---------|-------|
| **Definition** | Pipeline script from SCM |
| **SCM** | Git |
| **Repository URL** | Your `platform-infra-repo` remote |
| **Branch** | `*/master` |
| **Script Path** | `Jenkinsfile` |

## Agent requirements

- Docker and Docker Compose v2
- Agent user in the `docker` group (`/var/run/docker.sock` access)
- Repo checked out on the deploy host (e.g. `/opt/elt/platform-infra-repo`)
- Copy [`.env.example`](../.env.example) to `.env` on the server before first deploy

## One-time host bootstrap

```bash
docker network create elt-net
docker network create data-plane-net
```

## Pipeline stages

1. **Test** — all branches: [`jenkins/run-tests.sh`](run-tests.sh) (pytest in Docker)
2. **Deploy** — `master` only: [`deploy.sh`](../deploy.sh) (Jenkins uses [`jenkins/deploy-docker.sh`](deploy-docker.sh))
3. **Health** — `master` only: `curl http://127.0.0.1:9000/health` (localhost only; port 9000 is internal, not exposed publicly)

## Deploy ordering

| Scenario | Action |
|----------|--------|
| Fresh install | Deploy **platform-infra-repo** first, then etl-back, then elt-frontend |
| Infra code change | This Jenkins job only |
| `INTERNAL_SERVICE_TOKEN` change | Update `.env` here and in etl-back, redeploy both |
| etl-back change | etl-back Jenkins job; no infra redeploy needed |

## Verification

```bash
curl http://localhost:9000/health
docker ps | grep baas-infra-service
docker network ls | grep -E 'elt-net|data-plane-net'
```
