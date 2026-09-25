import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.infrastructure.config import Settings

COMMAND_KEY = "geo_command_test_key"


@pytest.fixture
def settings(tmp_path):
    return Settings(command_key=COMMAND_KEY, audit_log_path=tmp_path / "data" / "operation.log")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def command_headers():
    return {"X-API-KEY": COMMAND_KEY}


@pytest.fixture
def operator_headers(client, command_headers):
    response = client.post(
        "/admin/generate-key",
        json={"role": "OPERATOR", "owner_name": "Agent-07", "expires_in_days": 1},
        headers=command_headers,
    )
    return {"X-API-KEY": response.json()["api_key"]}
