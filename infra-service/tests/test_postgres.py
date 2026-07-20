"""Smoke tests for platform infra service (no Docker required)."""

from unittest.mock import patch

import pytest

from src.provisioners.postgres import (
    _provision_local_instance,
    _resolve_catalog_db,
    create_postgres_database,
    validate_schema_name,
)
from src.schemas import CreateDatabaseRequest, ServiceInstanceInfo


def test_validate_schema_name():
    assert validate_schema_name("analytics") == "analytics"


def test_validate_schema_name_rejects_public():
    with pytest.raises(ValueError):
        validate_schema_name("public")


def test_provision_local_instance_builds_service_info_without_duplicate_catalog_db():
    """meta already includes catalog_db; must not also pass it as a kwarg."""
    with (
        patch("src.provisioners.postgres.load_instance_meta", return_value=None),
        patch("src.provisioners.postgres.save_instance_meta"),
        patch(
            "src.provisioners.postgres.settings.LOCAL_POSTGRES_URL",
            "postgresql://elt:secret@dbhost:5432/dtorc_workspace",
        ),
    ):
        info = _provision_local_instance(1)

    assert isinstance(info, ServiceInstanceInfo)
    assert info.created is True
    assert info.catalog_db == "dtorc_workspace"
    assert info.host == "dbhost"
    assert info.port == 5432
    assert info.admin_user == "elt"


def test_resolve_catalog_db_rejects_legacy_app_default():
    with patch(
        "src.provisioners.postgres.settings.LOCAL_POSTGRES_URL",
        "postgresql://elt:secret@postgres:5432/dtorc_workspace",
    ):
        assert _resolve_catalog_db("app") == "dtorc_workspace"
        assert _resolve_catalog_db(None) == "dtorc_workspace"
        assert _resolve_catalog_db("analytics") == "analytics"


def test_create_postgres_database_passes_catalog_db_to_admin_url():
    instance = ServiceInstanceInfo(
        instance_ref="ws-1-postgres",
        container_name="local-shared",
        host="postgres",
        port=5432,
        admin_user="elt",
        admin_password="secret",
        catalog_db="dtorc_workspace",
        created=False,
    )
    with (
        patch(
            "src.provisioners.postgres._provision_local_instance",
            return_value=instance,
        ),
        patch(
            "src.provisioners.postgres.resolve_container_connect_host",
            return_value="postgres",
        ) as resolve_host,
        patch("src.provisioners.postgres.admin_url", return_value="postgresql://x") as admin,
        patch("src.provisioners.postgres._create_schema") as create_schema,
    ):
        create_postgres_database(
            CreateDatabaseRequest(workspace_id=1, engine="postgres", database_name="test_db")
        )

    resolve_host.assert_called_once_with("postgres")
    admin.assert_called_once_with("postgres", 5432, "elt", "secret", "dtorc_workspace")
    create_schema.assert_called_once_with("postgresql://x", "test_db")
