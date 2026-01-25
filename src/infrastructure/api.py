import os
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

load_dotenv()
from src.application.use_cases import GeoIntelligenceService
from src.infrastructure.logger_config import logger

# Security Settings
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Initialization of In-Memory Database
command_key = os.getenv("API_KEY_COMMAND")
api_keys_db = {}

if command_key:
    api_keys_db[command_key] = {"role": "COMMAND", "created_at": "static"}
else:
    print("CRITICAL: API_KEY_COMMAND not found in environment!")

# Security Dependency Function
async def get_api_key(api_key: str = Depends(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=403, detail="Access Denied: Missing Credentials")

    if api_key in api_keys_db:
        return api_keys_db[api_key]["role"]
    
    raise HTTPException(status_code=403, detail="Access Denied: Invalid Credentials")

app = FastAPI(title="Tactical Geo-Int API", version="1.0.0")

# --- SCHEMAS ---
class KeyGenerationRequest(BaseModel):
    role: str = "OPERATOR"
    expires_in_days: int = 30

class GeoRequest(BaseModel):
    origin: dict
    target: dict
    radius: float = 5.0

# --- ROUTES ---
@app.post("/admin/generate-key")
async def generate_new_key(
    request: KeyGenerationRequest, 
    admin_role: str = Depends(get_api_key)
):
    if admin_role != "COMMAND":
        raise HTTPException(status_code=403, detail="Insufficient permissions.")

    new_key = f"geo_{secrets.token_urlsafe(32)}"
    api_keys_db[new_key] = {
        "role": request.role,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=request.expires_in_days)).isoformat()
    }
    
    logger.info(f"New key generated for level {request.role}")
    return {
        "status": "key_generated",
        "api_key": new_key,
        "role": request.role,
        "expires_at": api_keys_db[new_key]["expires_at"]
    }

@app.post("/calculate")
async def calculate(request: GeoRequest, role: str = Depends(get_api_key)):
    try:
        # A API apenas repassa a missão para o Serviço de Aplicação
        result = GeoIntelligenceService.process_calculation(
            request.origin, request.target, request.radius
        )
        return {"status": "success", "role_access": role, "data": result}
    except Exception as e:
        logger.error(f"Erro tático: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))