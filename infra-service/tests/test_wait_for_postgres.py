"""Unit tests for Postgres readiness probing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.docker_driver import wait_for_postgres


@patch("src.docker_driver.time.sleep", return_value=None)
@patch("src.docker_driver.ensure_container_on_network")
@patch("src.docker_driver._container_ips", return_value=["172.28.0.9"])
@patch("src.docker_driver._postgres_ready")
@patch("src.docker_driver.subprocess.run")
def test_wait_for_postgres_falls_back_to_container_ip(
    mock_run,
    mock_ready,
    _mock_ips,
    _mock_ensure,
    _mock_sleep,
):
    inspect = MagicMock(returncode=0, stdout="running\n", stderr="")
    mock_run.return_value = inspect
    # Hostname probe fails; IP probe succeeds.
    mock_ready.side_effect = lambda host, port, user, password: (
        None if host == "172.28.0.9" else OSError("name resolution failed")
    )

    resolved = wait_for_postgres("ws-1-postgres-db", 5432, "baas", "secret", timeout=10)

    assert resolved == "172.28.0.9"
    assert mock_ready.call_count >= 2
    mock_ready.assert_any_call("ws-1-postgres-db", 5432, "baas", "secret")
    mock_ready.assert_any_call("172.28.0.9", 5432, "baas", "secret")


@patch("src.docker_driver.time.sleep", return_value=None)
@patch("src.docker_driver.time.time", side_effect=[0, 1, 200])
@patch("src.docker_driver.ensure_container_on_network")
@patch("src.docker_driver._container_ips", return_value=[])
@patch("src.docker_driver._postgres_ready", return_value=OSError("refused"))
@patch("src.docker_driver.subprocess.run")
def test_wait_for_postgres_times_out(
    mock_run,
    _mock_ready,
    _mock_ips,
    _mock_ensure,
    _mock_time,
    _mock_sleep,
):
    mock_run.return_value = MagicMock(returncode=0, stdout="running\n", stderr="")
    with pytest.raises(TimeoutError, match="Postgres not ready"):
        wait_for_postgres("ws-1-postgres-db", 5432, "baas", "secret", timeout=10)
