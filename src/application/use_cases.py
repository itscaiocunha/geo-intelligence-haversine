import csv
import io

from src.domain.entities import Coordinate, HaversineEngine
from src.infrastructure.logger_config import logger

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
    
    @staticmethod
    def process_batch_csv(csv_content: str, origin_data: dict, radius: float, role: str):
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)
        
        origin = Coordinate(origin_data['lat'], origin_data['lon'])
        results = []
        violations_count = 0

        for row in reader:
            try:
                target = Coordinate(float(row['lat']), float(row['lon']))
                target_name = row.get('name', 'Alvo Desconhecido')
                distance = HaversineEngine.calculate_distance(origin, target)
                alert = distance <= radius
                
                if alert:
                    violations_count += 1
                
                results.append({
                    "target": target_name,
                    "distance_km": round(distance, 2),
                    "violation": alert
                })
            except (ValueError, KeyError):
                continue

        # REGISTRO DE AUDITORIA: Agora o Batch deixa rastro no operation.log
        logger.info(
            f"BATCH_OPERATION | Role: {role} | Origin: {origin_data} | "
            f"Targets: {len(results)} | Violations: {violations_count}"
        )
        
        return {
            "summary": {
                "total_processed": len(results),
                "violations_detected": violations_count
            },
            "details": results
        }