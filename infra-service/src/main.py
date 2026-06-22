from fastapi import Depends, FastAPI, HTTPException

from src.auth import verify_internal_token
from src.provisioners import postgres as postgres_provisioner
from src.provisioners import redis as redis_provisioner
from src.schemas import (
    CreateDatabaseRequest,
    CreateDatabaseResponse,
    QueueBrokerRequest,
    QueueBrokerResponse,
)

app = FastAPI(title="BaaS Platform Infra Service", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/internal/projects/{workspace_id}/databases",
    response_model=CreateDatabaseResponse,
    dependencies=[Depends(verify_internal_token)],
)
def create_database(workspace_id: int, body: CreateDatabaseRequest):
    if body.workspace_id != workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id mismatch")

    if body.engine != "postgres":
        raise HTTPException(status_code=501, detail=f"Engine '{body.engine}' is not available yet")

    try:
        return postgres_provisioner.create_postgres_database(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Provisioning failed: {exc}") from exc


@app.post(
    "/internal/orgs/{org_id}/queue-brokers",
    response_model=QueueBrokerResponse,
    dependencies=[Depends(verify_internal_token)],
)
def provision_queue_broker(org_id: int, body: QueueBrokerRequest):
    if body.engine != "redis":
        raise HTTPException(status_code=501, detail=f"Engine '{body.engine}' is not available yet")
    try:
        from datetime import datetime, timezone

        result = redis_provisioner.provision_org_redis(org_id)
        return QueueBrokerResponse(
            instance_ref=result["instance_ref"],
            container_name=result["container_name"],
            host=result["host"],
            port=int(result["port"]),
            redis_url=result.get("redis_url"),
            created=bool(result.get("created")),
            provisioned_at=datetime.now(timezone.utc),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Queue broker provisioning failed: {exc}") from exc
