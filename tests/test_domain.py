import pytest

from src.domain import Coordinate, Credential, HaversineEngine

BRASILIA = Coordinate(-15.7942, -47.8822)
SAO_PAULO = Coordinate(-23.5505, -46.6333)


def test_distance_between_same_points():
    """It ensures that the distance to the same point is zero."""
    assert round(HaversineEngine.calculate_distance(BRASILIA, BRASILIA), 2) == 0.0


def test_sao_paulo_to_brasilia():
    """Validates the known distance between São Paulo and Brasília."""
    distance = HaversineEngine.calculate_distance(SAO_PAULO, BRASILIA)
    assert 870 <= distance <= 875


def test_distance_is_symmetric():
    assert HaversineEngine.calculate_distance(SAO_PAULO, BRASILIA) == pytest.approx(
        HaversineEngine.calculate_distance(BRASILIA, SAO_PAULO)
    )


def test_one_degree_on_equator():
    """One degree of arc equals 2πR/360 on a sphere of radius R."""
    distance = HaversineEngine.calculate_distance(Coordinate(0, 0), Coordinate(0, 1))
    assert distance == pytest.approx(111.19, abs=0.01)


def test_antipodal_points_are_half_circumference_apart():
    distance = HaversineEngine.calculate_distance(Coordinate(0, 0), Coordinate(0, 180))
    assert distance == pytest.approx(20015.09, abs=0.01)


def test_unit_conversion():
    """Verifies if the conversion to meters is operating correctly."""
    p1, p2 = Coordinate(0, 0), Coordinate(0, 1)
    dist_km = HaversineEngine.calculate_distance(p1, p2, unit="KM")
    dist_m = HaversineEngine.calculate_distance(p1, p2, unit="M")
    assert dist_m == dist_km * 1000


@pytest.mark.parametrize("lat, lon", [(100, 45), (-90.01, 0), (0, 180.5), (0, -181)])
def test_invalid_coordinates(lat, lon):
    """Validates if the system raises an error for physically impossible coordinates."""
    with pytest.raises(ValueError):
        Coordinate(lat, lon)


@pytest.mark.parametrize("lat, lon", [(90, 180), (-90, -180), (0, 0)])
def test_boundary_coordinates_are_valid(lat, lon):
    assert Coordinate(lat, lon) == Coordinate(lat, lon)


def test_geofencing_trigger():
    """Check if the active proximity alarm is working correctly."""
    near_target = Coordinate(-15.8000, -47.8900)

    assert HaversineEngine.is_within_radius(BRASILIA, near_target, radius=5.0) is True
    assert HaversineEngine.is_within_radius(BRASILIA, SAO_PAULO, radius=5.0) is False
    assert HaversineEngine.is_within_radius(BRASILIA, BRASILIA, radius=0) is True


def test_credential_agent_name_defaults_for_bootstrap_key():
    assert Credential(key="k", role="COMMAND").agent_name == "MASTER_SYSTEM"
    assert Credential(key="k", role="OPERATOR", owner="Agent-07").agent_name == "Agent-07"
