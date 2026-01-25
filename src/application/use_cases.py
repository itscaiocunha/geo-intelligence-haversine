from src.domain.entities import Coordinate, HaversineEngine

class GeoIntelligenceService:
    @staticmethod
    def process_calculation(origin_data: dict, target_data: dict, radius: float):
        origin = Coordinate(origin_data['lat'], origin_data['lon'])
        target = Coordinate(target_data['lat'], target_data['lon'])
        
        distance = HaversineEngine.calculate_distance(origin, target)
        alert = HaversineEngine.is_within_radius(origin, target, radius)
        
        return {
            "distance_km": round(distance, 2),
            "alert": alert,
            "message": "WARNING: Perimeter Violated!" if alert else "Area Secure."
        }