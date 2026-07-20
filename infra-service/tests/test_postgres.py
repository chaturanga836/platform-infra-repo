"""Smoke tests for platform infra service (no Docker required)."""

from unittest.mock import patch

import pytest

from src.provisioners.postgres import _provision_local_instance, validate_schema_name
from src.schemas import ServiceInstanceInfo


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
