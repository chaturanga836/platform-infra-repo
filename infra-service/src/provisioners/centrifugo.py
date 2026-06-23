"""Centrifugo: one container per organization for realtime notifications."""

from __future__ import annotations

import json
import secrets

from src.config import settings
from src.docker_driver import (
    broker_container_running,
    docker_compose_up,
    ensure_data_plane_network,
    load_instance_meta,
    org_container_name,
    org_instance_ref,
    render_org_centrifugo_compose,
    save_instance_meta,
    wait_for_centrifugo,
)


def _build_urls(host: str, port: int) -> dict[str, str]:
    return {
        "api_url": f"http://{host}:{port}",
        "ws_url": f"ws://{host}:{port}/connection/websocket",
    }


def provision_org_centrifugo(org_id: int) -> dict:
    ref = org_instance_ref(org_id, "centrifugo")
    existing = load_instance_meta(ref)
    if existing:
        container_name = existing.get("container_name") or org_container_name(org_id, "centrifugo")
        if broker_container_running(container_name):
            urls = _build_urls(existing["host"], int(existing["port"]))
            return {
                "instance_ref": ref,
                "container_name": container_name,
                "host": existing["host"],
                "port": int(existing["port"]),
                "api_url": existing.get("api_url") or urls["api_url"],
                "ws_url": existing.get("ws_url") or urls["ws_url"],
                "api_key": existing["api_key"],
                "token_hmac_secret_key": existing["token_hmac_secret_key"],
                "created": False,
            }

    if settings.PROVISION_MODE == "local":
        api_key = secrets.token_urlsafe(32)
        token_secret = secrets.token_urlsafe(32)
        host = "localhost"
        port = 8000
        urls = _build_urls(host, port)
        meta = {
            "org_id": org_id,
            "engine": "centrifugo",
            "instance_ref": ref,
            "container_name": f"{ref}-broker",
            "host": host,
            "port": port,
            "api_url": urls["api_url"],
            "ws_url": urls["ws_url"],
            "api_key": api_key,
            "token_hmac_secret_key": token_secret,
        }
        save_instance_meta(ref, meta)
        return {
            "instance_ref": ref,
            "container_name": meta["container_name"],
            "host": host,
            "port": port,
            "api_url": urls["api_url"],
            "ws_url": urls["ws_url"],
            "api_key": api_key,
            "token_hmac_secret_key": token_secret,
            "created": True,
        }

    api_key = secrets.token_urlsafe(32)
    token_secret = secrets.token_urlsafe(32)
    admin_password = secrets.token_urlsafe(24)
    admin_secret = secrets.token_urlsafe(24)

    ensure_data_plane_network()
    compose_file, config_path = render_org_centrifugo_compose(
        org_id,
        api_key=api_key,
        token_hmac_secret_key=token_secret,
        admin_password=admin_password,
        admin_secret=admin_secret,
    )
    docker_compose_up(compose_file, project_name=ref)
    host = org_container_name(org_id, "centrifugo")
    port = 8000
    wait_for_centrifugo(host, port)

    urls = _build_urls(host, port)
    meta = {
        "org_id": org_id,
        "engine": "centrifugo",
        "instance_ref": ref,
        "container_name": host,
        "host": host,
        "port": port,
        "api_url": urls["api_url"],
        "ws_url": urls["ws_url"],
        "api_key": api_key,
        "token_hmac_secret_key": token_secret,
        "config_path": str(config_path),
    }
    save_instance_meta(ref, meta)
    return {
        "instance_ref": ref,
        "container_name": host,
        "host": host,
        "port": port,
        "api_url": urls["api_url"],
        "ws_url": urls["ws_url"],
        "api_key": api_key,
        "token_hmac_secret_key": token_secret,
        "created": True,
    }
