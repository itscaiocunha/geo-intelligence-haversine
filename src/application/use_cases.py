import csv
import io
import os

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

        logger.info(
            f"BATCH_OPERATION | Agent: {role} | Origin: {origin_data} | "
            f"Targets: {len(results)} | Violations: {violations_count}"
        )
        
        return {
            "summary": {
                "total_processed": len(results),
                "violations_detected": violations_count
            },
            "details": results
        }

    @staticmethod
    def get_audit_stats():
        log_path = "data/operation.log"
        if not os.path.exists(log_path):
            return {"message": "Nenhum dado de auditoria disponível."}

        report = {
            "global_summary": {
                "total_entries": 0,
                "total_violations": 0,
                "operation_types": {"UNITARY": 0, "BATCH": 0, "KEY_GEN": 0}
            },
            "agents_detail": {} #
        }

        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                report["global_summary"]["total_entries"] += 1
                
                agent_name = None
                if "Agent: " in line:
                    agent_name = line.split("Agent: ")[1].split(" |")[0]
                elif "Issuer: " in line:
                    agent_name = line.split("Issuer: ")[1].split(" |")[0]
                elif "Batch processed by " in line:
                    agent_name = line.split("(")[1].split(")")[0] if "(" in line else "SYSTEM"

                if not agent_name:
                    continue

                if agent_name not in report["agents_detail"]:
                    report["agents_detail"][agent_name] = {
                        "total_ops": 0,
                        "unitary_calcs": 0,
                        "batch_calcs": 0,
                        "keys_generated": 0,
                        "violations_found": 0
                    }

                agent_data = report["agents_detail"][agent_name]
                agent_data["total_ops"] += 1

                if "CALC_UNITARY" in line:
                    agent_data["unitary_calcs"] += 1
                    report["global_summary"]["operation_types"]["UNITARY"] += 1
                    if "Perimeter Violated!" in line:
                        agent_data["violations_found"] += 1
                        report["global_summary"]["total_violations"] += 1
                
                elif "BATCH_OPERATION" in line or "Batch processed by" in line:
                    agent_data["batch_calcs"] += 1
                    report["global_summary"]["operation_types"]["BATCH"] += 1
                    if "Violations: " in line:
                        vCount = int(line.split("Violations: ")[1].strip())
                        agent_data["violations_found"] += vCount
                        report["global_summary"]["total_violations"] += vCount

                elif "KEY_GEN" in line:
                    agent_data["keys_generated"] += 1
                    report["global_summary"]["operation_types"]["KEY_GEN"] += 1

        return report