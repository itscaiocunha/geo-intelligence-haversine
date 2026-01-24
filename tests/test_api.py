import os
import pytest
from fastapi.testclient import TestClient
from src.api import app
from dotenv import load_dotenv

load_dotenv()
client = TestClient(app)

COMMAND_KEY = os.getenv("API_KEY_COMMAND")
COMMAND_HEADERS = {"X-API-KEY": COMMAND_KEY}

def test_admin_generate_key_flow():
    """
    Generate a dynamic key and validate its use.
    This test now serves as the basis for the others.
    """
    payload = {"role": "OPERATOR", "expires_in_days": 1}
    response = client.post("/admin/generate-key", json=payload, headers=COMMAND_HEADERS)
    
    assert response.status_code == 200
    new_key = response.json()["api_key"]
    
    op_headers = {"X-API-KEY": new_key}
    calc_payload = {
        "origin": {"lat": -15.7942, "lon": -47.8822},
        "target": {"lat": -15.8010, "lon": -47.8920}
    }
    calc_response = client.post("/calculate", json=calc_payload, headers=op_headers)
    assert calc_response.status_code == 200
    assert calc_response.json()["role_access"] == "OPERATOR"

def test_api_unauthorized_access():
    """Ensure the perimeter is closed to intruders."""
    payload = {"origin": {"lat": 0, "lon": 0}, "target": {"lat": 1, "lon": 1}}
    
    # Sem Header
    assert client.post("/calculate", json=payload).status_code == 403
    
    # Chave errada
    assert client.post("/calculate", json=payload, headers={"X-API-KEY": "fake"}).status_code == 403

def test_command_level_access():
    """It verifies whether the highest authority has direct access."""
    payload = {
        "origin": {"lat": -15.7942, "lon": -47.8822},
        "target": {"lat": -15.8010, "lon": -47.8920}
    }
    response = client.post("/calculate", json=payload, headers=COMMAND_HEADERS)
    assert response.status_code == 200
    assert response.json()["role_access"] == "COMMAND"