"""Postgres: one container per workspace; additional databases are schemas."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

from src.config import settings
from src.docker_driver import (
    admin_url,
    container_name,
    docker_compose_up,
    ensure_data_plane_network,
    instance_ref,
    load_instance_meta,
    render_compose,
    save_instance_meta,
    wait_for_postgres,
)
from src.schemas import CreateDatabaseRequest, CreateDatabaseResponse, DatabaseInfo, ServiceInstanceInfo

SCHEMA_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
RESERVED = frozenset({"public", "information_schema", "pg_catalog", "pg_toast"})


def validate_schema_name(name: str) -> str:
    normalized = name.strip().lower()
    if not SCHEMA_NAME_RE.match(normalized):
        raise ValueError(
            "Name must start with a letter, use lowercase letters, digits, "
            "underscores only, max 63 chars"
        )
    if normalized in RESERVED or normalized.startswith("pg_"):
        raise ValueError(f"Name '{normalized}' is reserved")
    return normalized


def _create_schema(admin_connection_url: str, schema_name: str) -> None:
    engine = create_engine(admin_connection_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
    finally:
        engine.dispose()


def _run_bootstrap(admin_connection_url: str) -> None:
    bootstrap = settings.STACKS_PATH / "project" / "postgres.bootstrap.pgsql"
    if not bootstrap.is_file():
        return
    sql = bootstrap.read_text(encoding="utf-8")
    engine = create_engine(admin_connection_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
    finally:
        engine.dispose()


def _provision_docker_instance(workspace_id: int) -> ServiceInstanceInfo:
    ref = instance_ref(workspace_id, "postgres")
    existing = load_instance_meta(ref)
    if existing:
        return ServiceInstanceInfo(
            instance_ref=ref,
            container_name=existing["container_name"],
            host=existing["host"],
            port=int(existing["port"]),
            admin_user=existing["admin_user"],
            admin_password=existing["admin_password"],
            created=False,
        )

    password = secrets.token_urlsafe(24)
    ensure_data_plane_network()
    compose_file = render_compose(workspace_id, "postgres", password)
    project_name = ref.replace("-", "_")
    docker_compose_up(compose_file, project_name)

    host = container_name(workspace_id, "postgres")
    wait_for_postgres(host, 5432, settings.POSTGRES_USER, password)
    admin_connection = admin_url(host, 5432, settings.POSTGRES_USER, password)
    _run_bootstrap(admin_connection)

    meta = {
        "instance_ref": ref,
        "container_name": container_name(workspace_id, "postgres"),
        "host": host,
        "port": 5432,
        "admin_user": settings.POSTGRES_USER,
        "admin_password": password,
    }
    save_instance_meta(ref, meta)
    return ServiceInstanceInfo(created=True, **meta)


def _provision_local_instance(workspace_id: int) -> ServiceInstanceInfo:
    """Dev fallback: one logical instance per workspace on shared LOCAL_POSTGRES_URL."""
    ref = instance_ref(workspace_id, "postgres")
    existing = load_instance_meta(ref)
    if existing:
        return ServiceInstanceInfo(
            instance_ref=ref,
            container_name=existing.get("container_name", "local-shared"),
            host=existing["host"],
            port=int(existing["port"]),
            admin_user=existing["admin_user"],
            admin_password=existing["admin_password"],
            created=False,
        )

    from urllib.parse import urlparse

    parsed = urlparse(settings.LOCAL_POSTGRES_URL)
    user = parsed.username or "postgres"
    password = parsed.password or ""
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432

    meta = {
        "instance_ref": ref,
        "container_name": "local-shared",
        "host": host,
        "port": port,
        "admin_user": user,
        "admin_password": password,
    }
    save_instance_meta(ref, meta)
    return ServiceInstanceInfo(created=True, **meta)


def create_postgres_database(body: CreateDatabaseRequest) -> CreateDatabaseResponse:
    schema_name = validate_schema_name(body.database_name)

    if body.existing_instance:
        instance = ServiceInstanceInfo(
            instance_ref=body.existing_instance.instance_ref,
            container_name=body.existing_instance.container_name,
            host=body.existing_instance.host,
            port=body.existing_instance.port,
            admin_user=body.existing_instance.admin_user,
            admin_password=body.existing_instance.admin_password,
            created=False,
        )
    elif settings.PROVISION_MODE == "docker":
        instance = _provision_docker_instance(body.workspace_id)
    else:
        instance = _provision_local_instance(body.workspace_id)

    admin_connection = admin_url(
        instance.host,
        instance.port,
        instance.admin_user,
        instance.admin_password,
    )
    _create_schema(admin_connection, schema_name)

    return CreateDatabaseResponse(
        instance=instance,
        database=DatabaseInfo(name=schema_name, engine="postgres", status="ready"),
        provisioned_at=datetime.now(timezone.utc),
    )
