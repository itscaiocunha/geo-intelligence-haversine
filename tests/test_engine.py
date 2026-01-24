import pytest
from src.engine import Coordinate, HaversineEngine

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
    p2 = Coordinate(0, 1) # ~111km na linha do equador
    dist_km = HaversineEngine.calculate_distance(p1, p2, unit="KM")
    dist_m = HaversineEngine.calculate_distance(p1, p2, unit="M")
    assert dist_m == dist_km * 1000

def test_geofencing_trigger():
    """Testa se o alarme de proximidade ativa corretamente."""
    base = Coordinate(-15.7942, -47.8822) # Brasília
    alvo_perto = Coordinate(-15.8000, -47.8900) # Muito próximo
    alvo_longe = Coordinate(-23.5505, -46.6333) # SP
    
    assert HaversineEngine.is_within_radius(base, alvo_perto, radius=5.0) is True
    assert HaversineEngine.is_within_radius(base, alvo_longe, radius=5.0) is False