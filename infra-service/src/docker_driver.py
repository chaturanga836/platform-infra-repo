"""Docker compose helpers for per-project postgres containers."""

from __future__ import annotations

import json
import secrets
import subprocess
import time
from pathlib import Path
from typing import Any, Dict
from urllib.parse import quote_plus

from src.config import settings


def instance_ref(workspace_id: int, engine: str) -> str:
    return f"ws-{workspace_id}-{engine}"


def container_name(workspace_id: int, engine: str) -> str:
    return f"{instance_ref(workspace_id, engine)}-db"


def org_instance_ref(org_id: int, engine: str) -> str:
    return f"org-{org_id}-{engine}"


def org_container_name(org_id: int, engine: str) -> str:
    return f"{org_instance_ref(org_id, engine)}-broker"


def _instance_meta_path(ref: str) -> Path:
    path = settings.INSTANCES_DATA_PATH / f"{ref}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_instance_meta(ref: str, meta: Dict[str, Any]) -> None:
    _instance_meta_path(ref).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def load_instance_meta(ref: str) -> Dict[str, Any] | None:
    path = _instance_meta_path(ref)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def render_compose(workspace_id: int, engine: str, password: str) -> Path:
    template_path = settings.STACKS_PATH / "project" / f"{engine}.compose.template.yml"
    if not template_path.is_file():
        raise FileNotFoundError(f"Missing stack template: {template_path}")

    ref = instance_ref(workspace_id, engine)
    out_dir = settings.INSTANCES_DATA_PATH / ref
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "docker-compose.yml"

    content = template_path.read_text(encoding="utf-8")
    content = content.replace("${POSTGRES_IMAGE}", settings.POSTGRES_IMAGE)
    content = content.replace("${INSTANCE_REF}", ref)
    content = content.replace("${CONTAINER_NAME}", container_name(workspace_id, engine))
    content = content.replace("${POSTGRES_PASSWORD}", password)
    content = content.replace("${POSTGRES_USER}", settings.POSTGRES_USER)
    content = content.replace("${POSTGRES_DB}", settings.POSTGRES_DB)
    content = content.replace("${POSTGRES_IMAGE}", settings.POSTGRES_IMAGE)
    content = content.replace("${DATA_PLANE_NETWORK}", settings.DATA_PLANE_NETWORK)
    out_file.write_text(content, encoding="utf-8")
    return out_file


def render_org_centrifugo_compose(
    org_id: int,
    *,
    api_key: str,
    token_hmac_secret_key: str,
    admin_password: str,
    admin_secret: str,
) -> tuple[Path, Path]:
    compose_template = settings.STACKS_PATH / "project" / "centrifugo.compose.template.yml"
    config_template = settings.STACKS_PATH / "project" / "centrifugo.config.template.json"
    if not compose_template.is_file():
        raise FileNotFoundError(f"Missing stack template: {compose_template}")
    if not config_template.is_file():
        raise FileNotFoundError(f"Missing config template: {config_template}")

    ref = org_instance_ref(org_id, "centrifugo")
    out_dir = settings.INSTANCES_DATA_PATH / ref
    out_dir.mkdir(parents=True, exist_ok=True)
    compose_file = out_dir / "docker-compose.yml"
    config_file = out_dir / "config.json"

    config_content = config_template.read_text(encoding="utf-8")
    config_content = config_content.replace("${TOKEN_HMAC_SECRET}", token_hmac_secret_key)
    config_content = config_content.replace("${API_KEY}", api_key)
    config_content = config_content.replace("${ADMIN_PASSWORD}", admin_password)
    config_content = config_content.replace("${ADMIN_SECRET}", admin_secret)
    config_file.write_text(config_content, encoding="utf-8")

    content = compose_template.read_text(encoding="utf-8")
    content = content.replace("${CENTRIFUGO_IMAGE}", settings.CENTRIFUGO_IMAGE)
    content = content.replace("${INSTANCE_REF}", ref)
    content = content.replace("${CONTAINER_NAME}", org_container_name(org_id, "centrifugo"))
    content = content.replace("${CONFIG_PATH}", str(config_file.resolve()))
    content = content.replace("${DATA_PLANE_NETWORK}", settings.DATA_PLANE_NETWORK)
    compose_file.write_text(content, encoding="utf-8")
    return compose_file, config_file


def wait_for_centrifugo(host: str, port: int, timeout: int = 60) -> None:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    url = f"http://{host}:{port}/health"
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2)
    raise TimeoutError(f"Centrifugo not ready at {host}:{port}: {last_err}")


def render_org_compose(org_id: int, engine: str, password: str) -> Path:
    template_path = settings.STACKS_PATH / "project" / f"{engine}.compose.template.yml"
    if not template_path.is_file():
        raise FileNotFoundError(f"Missing stack template: {template_path}")

    ref = org_instance_ref(org_id, engine)
    out_dir = settings.INSTANCES_DATA_PATH / ref
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "docker-compose.yml"

    content = template_path.read_text(encoding="utf-8")
    content = content.replace("${REDIS_IMAGE}", settings.REDIS_IMAGE)
    content = content.replace("${INSTANCE_REF}", ref)
    content = content.replace("${CONTAINER_NAME}", org_container_name(org_id, engine))
    content = content.replace("${REDIS_PASSWORD}", password)
    content = content.replace("${DATA_PLANE_NETWORK}", settings.DATA_PLANE_NETWORK)
    out_file.write_text(content, encoding="utf-8")
    return out_file


def docker_compose_up(compose_file: Path, project_name: str) -> None:
    cmd = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "-p",
        project_name,
        "up",
        "-d",
        "--remove-orphans",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"Command {cmd!r} returned non-zero exit status {result.returncode}"
            + (f": {detail}" if detail else "")
        )


def wait_for_postgres(host: str, port: int, user: str, password: str, timeout: int = 90) -> None:
    import psycopg2

    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=settings.POSTGRES_DB,
                connect_timeout=3,
            )
            conn.close()
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2)
    raise TimeoutError(f"Postgres not ready at {host}:{port}: {last_err}")


def wait_for_redis(host: str, port: int, password: str | None = None, timeout: int = 60) -> None:
    import redis

    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            client = redis.Redis(
                host=host,
                port=port,
                password=password,
                socket_connect_timeout=3,
            )
            client.ping()
            client.close()
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2)
    raise TimeoutError(f"Redis not ready at {host}:{port}: {last_err}")


def admin_url(host: str, port: int, user: str, password: str, dbname: str | None = None) -> str:
    db = dbname or settings.POSTGRES_DB
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db}"


def ensure_data_plane_network() -> None:
    result = subprocess.run(
        ["docker", "network", "inspect", settings.DATA_PLANE_NETWORK],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        subprocess.run(
            ["docker", "network", "create", settings.DATA_PLANE_NETWORK],
            check=True,
            capture_output=True,
            text=True,
        )
