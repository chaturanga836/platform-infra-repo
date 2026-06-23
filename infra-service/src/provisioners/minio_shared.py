"""Platform-wide shared MinIO for trial workspaces."""

from __future__ import annotations

import secrets

from src.config import settings
from src.docker_driver import (
    docker_compose_up,
    ensure_data_plane_network,
    load_instance_meta,
    platform_container_name,
    platform_instance_ref,
    render_platform_minio_compose,
    save_instance_meta,
    wait_for_minio,
)
from src.minio_utils import ensure_bucket

SHARED_REF = platform_instance_ref("minio")
SHARED_HOST = platform_container_name("minio")
SHARED_PORT = 9000


def ensure_shared_minio() -> dict:
    existing = load_instance_meta(SHARED_REF)
    if existing:
        return {
            "instance_ref": SHARED_REF,
            "container_name": existing["container_name"],
            "host": existing["host"],
            "port": int(existing["port"]),
            "endpoint_url": existing["endpoint_url"],
            "bucket": existing["bucket"],
            "access_key": existing["access_key"],
            "secret_key": existing["secret_key"],
            "created": False,
        }

    if settings.PROVISION_MODE == "local":
        endpoint_url = settings.LOCAL_MINIO_ENDPOINT.rstrip("/")
        access_key = settings.LOCAL_MINIO_ACCESS_KEY
        secret_key = settings.LOCAL_MINIO_SECRET_KEY
        meta = {
            "instance_ref": SHARED_REF,
            "container_name": "local-shared-minio",
            "host": endpoint_url.replace("http://", "").replace("https://", "").split(":")[0],
            "port": 9000,
            "endpoint_url": endpoint_url,
            "bucket": settings.SHARED_MINIO_BUCKET,
            "access_key": access_key,
            "secret_key": secret_key,
        }
        save_instance_meta(SHARED_REF, meta)
        try:
            ensure_bucket(endpoint_url, access_key, secret_key, settings.SHARED_MINIO_BUCKET)
        except Exception:  # noqa: BLE001
            pass
        return {**meta, "created": True}

    access_key = secrets.token_urlsafe(16)
    secret_key = secrets.token_urlsafe(32)
    ensure_data_plane_network()
    compose_file = render_platform_minio_compose(access_key, secret_key)
    docker_compose_up(compose_file, project_name=SHARED_REF.replace("-", "_"))
    wait_for_minio(SHARED_HOST, SHARED_PORT)

    endpoint_url = f"http://{SHARED_HOST}:{SHARED_PORT}"
    ensure_bucket(endpoint_url, access_key, secret_key, settings.SHARED_MINIO_BUCKET)

    meta = {
        "instance_ref": SHARED_REF,
        "container_name": SHARED_HOST,
        "host": SHARED_HOST,
        "port": SHARED_PORT,
        "endpoint_url": endpoint_url,
        "bucket": settings.SHARED_MINIO_BUCKET,
        "access_key": access_key,
        "secret_key": secret_key,
    }
    save_instance_meta(SHARED_REF, meta)
    return {**meta, "created": True}


def allocate_shared_prefix(org_id: int, workspace_id: int) -> dict:
    shared = ensure_shared_minio()
    prefix = f"data/{org_id}/{workspace_id}/"
    return {
        "mode": "shared",
        "instance_ref": shared["instance_ref"],
        "container_name": shared["container_name"],
        "host": shared["host"],
        "port": int(shared["port"]),
        "endpoint_url": shared["endpoint_url"],
        "bucket": shared["bucket"],
        "prefix": prefix,
        "access_key": shared["access_key"],
        "secret_key": shared["secret_key"],
        "created": bool(shared.get("created")),
    }
