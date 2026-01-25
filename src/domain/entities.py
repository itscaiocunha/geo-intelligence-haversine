import math
from dataclasses import dataclass

@dataclass(frozen=True)
class Coordinate:
    lat: float
    lon: float

    def __post_init__(self):
        if not (-90 <= self.lat <= 90):
            raise ValueError("Latitude deve estar entre -90 e 90.")
        if not (-180 <= self.lon <= 180):
            raise ValueError("Longitude deve estar entre -180 e 180.")

class HaversineEngine:
    EARTH_RADIUS_KM = 6371.0

    @staticmethod
    def calculate_distance(p1: Coordinate, p2: Coordinate, unit: str = "KM") -> float:
        dlat = math.radians(p2.lat - p1.lat)
        dlon = math.radians(p2.lon - p1.lon)
        
        a = (math.sin(dlat / 2)**2 + 
             math.cos(math.radians(p1.lat)) * math.cos(math.radians(p2.lat)) * math.sin(dlon / 2)**2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_km = HaversineEngine.EARTH_RADIUS_KM * c
        
        return distance_km if unit == "KM" else distance_km * 1000

    @staticmethod
    def is_within_radius(p1: Coordinate, p2: Coordinate, radius: float) -> bool:
        return HaversineEngine.calculate_distance(p1, p2) <= radius