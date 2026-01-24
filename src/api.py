import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.engine import Coordinate, HaversineEngine
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from dotenv import load_dotenv

load_dotenv()

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Authorized keys
AUTHORIZED_KEYS = {
    os.getenv("API_KEY_OPERATOR"): "OPERATOR",
    os.getenv("API_KEY_COMMAND"): "COMMAND"
}

async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key in AUTHORIZED_KEYS:
        return AUTHORIZED_KEYS[api_key]
    raise HTTPException(status_code=403, detail="Access Denied: Invalid Credentials")

app = FastAPI(title="Tactical Geo-Int API", version="1.0.0")

# Data Schema (Pydantic) for automatic JSON validation
class GeoRequest(BaseModel):
    origin: dict
    target: dict
    radius: float = 5.0

@app.post("/calculate")
async def calculate_tactical_distance(
    request: GeoRequest,
    role: str = Depends(get_api_key) # Security dependency injection
    ):
    try:
        # Conversion of the received JSON
        origin_coord = Coordinate(request.origin['lat'], request.origin['lon'])
        target_coord = Coordinate(request.target['lat'], request.target['lon'])
        
        distance = HaversineEngine.calculate_distance(origin_coord, target_coord)
        within = HaversineEngine.is_within_radius(origin_coord, target_coord, request.radius)
        
        return {
            "status": "success",
            "role_access": role,
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