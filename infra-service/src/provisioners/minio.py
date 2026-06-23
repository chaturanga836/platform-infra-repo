"""Dedicated MinIO container per workspace (gold/platinum)."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from src.config import settings
from src.docker_driver import (
    container_name,
    docker_compose_up,
    ensure_data_plane_network,
    instance_ref,
    load_instance_meta,
    render_minio_compose,
    save_instance_meta,
    wait_for_minio,
)
from src.minio_utils import ensure_bucket
from src.schemas import ExistingMinioInstance, ProvisionStorageRequest, ProvisionStorageResponse


def _provision_docker_instance(workspace_id: int) -> dict:
    ref = instance_ref(workspace_id, "minio")
    existing = load_instance_meta(ref)
    if existing:
        return {
            "instance_ref": ref,
            "container_name": existing["container_name"],
            "host": existing["host"],
            "port": int(existing["port"]),
            "endpoint_url": existing["endpoint_url"],
            "bucket": existing.get("bucket", settings.DEDICATED_MINIO_BUCKET),
            "access_key": existing["access_key"],
            "secret_key": existing["secret_key"],
            "created": False,
        }

    access_key = secrets.token_urlsafe(16)
    secret_key = secrets.token_urlsafe(32)
    ensure_data_plane_network()
    compose_file = render_minio_compose(workspace_id, access_key, secret_key)
    docker_compose_up(compose_file, project_name=ref.replace("-", "_"))
    host = container_name(workspace_id, "minio")
    port = 9000
    wait_for_minio(host, port)

    endpoint_url = f"http://{host}:{port}"
    bucket = settings.DEDICATED_MINIO_BUCKET
    ensure_bucket(endpoint_url, access_key, secret_key, bucket)

    meta = {
        "instance_ref": ref,
        "container_name": host,
        "host": host,
        "port": port,
        "endpoint_url": endpoint_url,
        "bucket": bucket,
        "access_key": access_key,
        "secret_key": secret_key,
    }
    save_instance_meta(ref, meta)
    return {**meta, "created": True}


def _provision_local_instance(workspace_id: int) -> dict:
    ref = instance_ref(workspace_id, "minio")
    existing = load_instance_meta(ref)
    if existing:
        return {
            "instance_ref": ref,
            "container_name": existing.get("container_name", "local-dedicated-minio"),
            "host": existing["host"],
            "port": int(existing["port"]),
            "endpoint_url": existing["endpoint_url"],
            "bucket": existing.get("bucket", settings.DEDICATED_MINIO_BUCKET),
            "access_key": existing["access_key"],
            "secret_key": existing["secret_key"],
            "created": False,
        }

    endpoint_url = settings.LOCAL_MINIO_ENDPOINT.rstrip("/")
    access_key = settings.LOCAL_MINIO_ACCESS_KEY
    secret_key = settings.LOCAL_MINIO_SECRET_KEY
    bucket = settings.DEDICATED_MINIO_BUCKET
    meta = {
        "instance_ref": ref,
        "container_name": f"local-ws-{workspace_id}-minio",
        "host": endpoint_url.replace("http://", "").replace("https://", "").split(":")[0],
        "port": 9000,
        "endpoint_url": endpoint_url,
        "bucket": bucket,
        "access_key": access_key,
        "secret_key": secret_key,
    }
    save_instance_meta(ref, meta)
    try:
        ensure_bucket(endpoint_url, access_key, secret_key, bucket)
    except Exception:  # noqa: BLE001
        pass
    return {**meta, "created": True}


def provision_workspace_storage(body: ProvisionStorageRequest) -> ProvisionStorageResponse:
    if body.mode == "shared":
        from src.provisioners.minio_shared import allocate_shared_prefix

        result = allocate_shared_prefix(body.org_id, body.workspace_id)
        return ProvisionStorageResponse(
            mode="shared",
            instance_ref=result["instance_ref"],
            container_name=result["container_name"],
            host=result["host"],
            port=int(result["port"]),
            endpoint_url=result["endpoint_url"],
            bucket=result["bucket"],
            prefix=result["prefix"],
            access_key=result["access_key"],
            secret_key=result["secret_key"],
            created=bool(result.get("created")),
            provisioned_at=datetime.now(timezone.utc),
        )

    if body.existing_instance:
        instance = body.existing_instance
        return ProvisionStorageResponse(
            mode="dedicated",
            instance_ref=instance.instance_ref,
            container_name=instance.container_name,
            host=instance.host,
            port=instance.port,
            endpoint_url=instance.endpoint_url,
            bucket=instance.bucket,
            prefix="",
            access_key=instance.access_key,
            secret_key=instance.secret_key,
            created=False,
            provisioned_at=datetime.now(timezone.utc),
        )

    if settings.PROVISION_MODE == "docker":
        result = _provision_docker_instance(body.workspace_id)
    else:
        result = _provision_local_instance(body.workspace_id)

    return ProvisionStorageResponse(
        mode="dedicated",
        instance_ref=result["instance_ref"],
        container_name=result["container_name"],
        host=result["host"],
        port=int(result["port"]),
        endpoint_url=result["endpoint_url"],
        bucket=result["bucket"],
        prefix="",
        access_key=result["access_key"],
        secret_key=result["secret_key"],
        created=bool(result.get("created")),
        provisioned_at=datetime.now(timezone.utc),
    )
