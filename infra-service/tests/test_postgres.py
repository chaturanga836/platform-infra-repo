"""Smoke tests for platform infra service (no Docker required)."""

from src.provisioners.postgres import validate_schema_name
import pytest


def test_validate_schema_name():
    assert validate_schema_name("analytics") == "analytics"


def test_validate_schema_name_rejects_public():
    with pytest.raises(ValueError):
        validate_schema_name("public")
