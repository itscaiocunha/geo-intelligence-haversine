import math

from src.domain.coordinate import Coordinate


class HaversineEngine:
    """Great-circle distance on a spherical Earth model (Sinnott, 1984)."""

    EARTH_RADIUS_KM = 6371.0

    @staticmethod
    def calculate_distance(p1: Coordinate, p2: Coordinate, unit: str = "KM") -> float:
        """Distance between two points, in kilometers ("KM") or meters (any other unit)."""
        dlat = math.radians(p2.lat - p1.lat)
        dlon = math.radians(p2.lon - p1.lon)

        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(p1.lat)) * math.cos(math.radians(p2.lat)) * math.sin(dlon / 2) ** 2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_km = HaversineEngine.EARTH_RADIUS_KM * c

        return distance_km if unit == "KM" else distance_km * 1000

    @staticmethod
    def is_within_radius(p1: Coordinate, p2: Coordinate, radius: float) -> bool:
        """True when p2 lies inside (or on the edge of) the circle of `radius` km around p1."""
        return HaversineEngine.calculate_distance(p1, p2) <= radius
