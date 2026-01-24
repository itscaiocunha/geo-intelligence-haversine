from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.engine import Coordinate, HaversineEngine

app = FastAPI(title="Tactical Geo-Int API", version="1.0.0")

# Data Schema (Pydantic) for automatic JSON validation
class GeoRequest(BaseModel):
    origin: dict
    target: dict
    radius: float = 5.0

@app.post("/calculate")
async def calculate_tactical_distance(request: GeoRequest):
    try:
        # Conversion of the received JSON
        origin_coord = Coordinate(request.origin['lat'], request.origin['lon'])
        target_coord = Coordinate(request.target['lat'], request.target['lon'])
        
        distance = HaversineEngine.calculate_distance(origin_coord, target_coord)
        within = HaversineEngine.is_within_radius(origin_coord, target_coord, request.radius)
        
        return {
            "status": "success",
            "code": 200,
            "data": {
                "distance_km": round(distance, 2),
                "alert": within,
                "message": "Target within perimeter!" if within else "Target clear."
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "operational", "system": "GEO-INT Engine"}