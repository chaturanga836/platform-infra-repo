"""Redis: one container per organization for queue broker."""

from __future__ import annotations

import secrets

from src.config import settings
from src.docker_driver import (
    docker_compose_up,
    ensure_data_plane_network,
    load_instance_meta,
    org_container_name,
    org_instance_ref,
    render_org_compose,
    save_instance_meta,
    wait_for_redis,
)


def provision_org_redis(org_id: int) -> dict:
    ref = org_instance_ref(org_id, "redis")
    existing = load_instance_meta(ref)
    if existing:
        return {
            "instance_ref": ref,
            "container_name": existing["container_name"],
            "host": existing["host"],
            "port": int(existing["port"]),
            "redis_url": existing["redis_url"],
            "created": False,
        }

    if settings.PROVISION_MODE == "local":
        url = settings.LOCAL_REDIS_URL
        meta = {
            "org_id": org_id,
            "engine": "redis",
            "instance_ref": ref,
            "container_name": f"{ref}-redis",
            "host": "localhost",
            "port": 6379,
            "redis_url": url,
        }
        save_instance_meta(ref, meta)
        return {
            "instance_ref": ref,
            "container_name": meta["container_name"],
            "host": meta["host"],
            "port": meta["port"],
            "redis_url": url,
            "created": True,
        }

    password = secrets.token_urlsafe(24)
    ensure_data_plane_network()
    compose_file = render_org_compose(org_id, "redis", password)
    docker_compose_up(compose_file, project_name=ref)
    host = org_container_name(org_id, "redis")
    port = 6379
    wait_for_redis(host, port, password=password)

    redis_url = f"redis://:{password}@{host}:{port}/0"
    meta = {
        "org_id": org_id,
        "engine": "redis",
        "instance_ref": ref,
        "container_name": host,
        "host": host,
        "port": port,
        "redis_password": password,
        "redis_url": redis_url,
    }
    save_instance_meta(ref, meta)
    return {
        "instance_ref": ref,
        "container_name": host,
        "host": host,
        "port": port,
        "redis_url": redis_url,
        "created": True,
    }
