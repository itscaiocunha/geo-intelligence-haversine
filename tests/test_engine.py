import os
import pytest

from fastapi.testclient import TestClient
from src.api import app
from src.engine import Coordinate, HaversineEngine
from dotenv import load_dotenv

load_dotenv()
client = TestClient(app)

VALID_API_KEY = os.getenv("API_KEY_OPERATOR")
HEADERS = {"X-API-KEY": VALID_API_KEY}

# Authorized keys
AUTHORIZED_KEYS = {
    os.getenv("API_KEY_OPERATOR"): "OPERATOR",
    os.getenv("API_KEY_COMMAND"): "COMMAND"
}

def test_distance_between_same_points():
    """It ensures that the distance to the same point is zero."""
    p1 = Coordinate(-15.7942, -47.8822)
    distance = HaversineEngine.calculate_distance(p1, p1)
    assert round(distance, 2) == 0.0

def test_sao_paulo_to_brasilia():
    """Validates the known distance between São Paulo and Brasília."""
    sp = Coordinate(-23.5505, -46.6333)
    bsb = Coordinate(-15.7942, -47.8822)
    distance = HaversineEngine.calculate_distance(sp, bsb)
    assert 870 <= distance <= 875  # Margem de tolerância aceitável

def test_invalid_latitude():
    """Validates if the system raises an error for physically impossible coordinates."""
    with pytest.raises(ValueError):
        Coordinate(100, 45)  # Latitude maximum is 90

def test_unit_conversion():
    """Verifies if the conversion to meters is operating correctly."""
    p1 = Coordinate(0, 0)
    p2 = Coordinate(0, 1)
    dist_km = HaversineEngine.calculate_distance(p1, p2, unit="KM")
    dist_m = HaversineEngine.calculate_distance(p1, p2, unit="M")
    assert dist_m == dist_km * 1000

def test_geofencing_trigger():
    """Check if the active proximity alarm is working correctly."""
    base = Coordinate(-15.7942, -47.8822) # Brasília
    alvo_perto = Coordinate(-15.8000, -47.8900) # Very close
    alvo_longe = Coordinate(-23.5505, -46.6333) # SP
    
    assert HaversineEngine.is_within_radius(base, alvo_perto, radius=5.0) is True
    assert HaversineEngine.is_within_radius(base, alvo_longe, radius=5.0) is False

client = TestClient(app)
def test_api_calculate_success():
    """Validates the main endpoint with valid data."""
    payload = {
        "origin": {"lat": -15.7942, "lon": -47.8822},
        "target": {"lat": -23.5505, "lon": -46.6333},
        "radius": 10.0
    }
    response = client.post("/calculate", json=payload, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["distance_km"] > 800
    assert data["data"]["alert"] is False

def test_api_invalid_data():
    """Ensures that the API blocks impossible coordinates (Business Rule)."""
    payload = {
        "origin": {"lat": 100.0, "lon": 0.0},
        "target": {"lat": 0.0, "lon": 0.0}
    }
    response = client.post("/calculate", json=payload, headers=HEADERS)
    assert response.status_code == 400

def test_api_calculate_success_with_auth():
    """Valida o cálculo quando as credenciais estão corretas."""
    payload = {
        "origin": {"lat": -15.7942, "lon": -47.8822},
        "target": {"lat": -23.5505, "lon": -46.6333},
        "radius": 10.0
    }
    # Injeção tática do Header de segurança
    response = client.post("/calculate", json=payload, headers=HEADERS)
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["role_access"] == "OPERATOR"

def test_api_unauthorized_access():
    """Garante que o acesso sem chave ou com chave errada seja bloqueado (403)."""
    payload = {"origin": {"lat": 0, "lon": 0}, "target": {"lat": 1, "lon": 1}}
    
    # Tentativa de invasão sem Header
    response = client.post("/calculate", json=payload)
    assert response.status_code == 403
    
    # Tentativa com chave corrompida
    bad_headers = {"X-API-KEY": "wrong-key-123"}
    response = client.post("/calculate", json=payload, headers=bad_headers)
    assert response.status_code == 403

def test_command_level_access():
    """Valida se o nível COMMAND é identificado corretamente."""
    command_key = os.getenv("API_KEY_COMMAND")
    headers = {"X-API-KEY": command_key}
    
    payload = {
        "origin": {"lat": -15.7942, "lon": -47.8822},
        "target": {"lat": -15.8010, "lon": -47.8920}
    }
    
    response = client.post("/calculate", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["role_access"] == "COMMAND"