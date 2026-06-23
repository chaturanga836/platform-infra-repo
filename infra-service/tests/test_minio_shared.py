"""Unit tests for MinIO shared provisioner helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.provisioners.minio_shared import allocate_shared_prefix


@patch("src.provisioners.minio_shared.ensure_shared_minio")
def test_allocate_shared_prefix(mock_ensure):
    mock_ensure.return_value = {
        "instance_ref": "platform-shared-minio",
        "container_name": "platform-shared-minio-storage",
        "host": "platform-shared-minio-storage",
        "port": 9000,
        "endpoint_url": "http://platform-shared-minio-storage:9000",
        "bucket": "crypto-lake",
        "access_key": "ak",
        "secret_key": "sk",
        "created": False,
    }
    result = allocate_shared_prefix(org_id=10, workspace_id=25)
    assert result["mode"] == "shared"
    assert result["prefix"] == "data/10/25/"
    assert result["bucket"] == "crypto-lake"
