import os
import secrets

from datetime import datetime, timedelta
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi import UploadFile, File, Form

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
        logger.warning("ACESSO NEGADO: Tentativa de acesso sem credenciais.")
        raise HTTPException(status_code=403, detail="Access Denied: Missing Credentials")

    if api_key in api_keys_db:
        user_info = api_keys_db[api_key].copy()
        user_info["key_fragment"] = f"{api_key[:8]}..."
        return user_info
    
    logger.warning("ACESSO NEGADO: Chave inválida detectada.")
    raise HTTPException(status_code=403, detail="Access Denied: Invalid Credentials")

app = FastAPI(title="Tactical Geo-Int API", version="1.0.0")

# --- SCHEMAS ---
class KeyGenerationRequest(BaseModel):
    role: str = "OPERATOR"
    owner_name: str 
    expires_in_days: int = 30

class GeoRequest(BaseModel):
    origin: dict
    target: dict
    radius: float = 5.0

# --- ROUTES ---
@app.post("/admin/generate-key")
async def generate_new_key(request: KeyGenerationRequest, user: dict = Depends(get_api_key), api_key: str = Security(api_key_header)):
    issuer = api_keys_db.get(api_key, {}).get("owner", "MASTER_SYSTEM")

    if user["role"] != "COMMAND":
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    issuer = user.get("owner", "MASTER_SYSTEM")

    new_key = f"geo_{secrets.token_urlsafe(32)}"
    api_keys_db[new_key] = {
        "role": request.role,
        "owner": request.owner_name,
        "issuer": issuer,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=request.expires_in_days)).isoformat()
    }
    
    logger.info(f"KEY_GEN | Issuer: {issuer} | Recipient: {request.owner_name} | Role: {request.role}")
    return {
        "status": "key_generated",
        "api_key": new_key,
        "role": request.role,
        "expires_at": api_keys_db[new_key]["expires_at"]
    }

@app.get("/admin/stats")
async def get_system_stats(user: dict = Depends(get_api_key)):
    if user["role"] != "COMMAND":
        logger.warning(f"ACCESS DENIED: Operator attempted to access admin statistics.")
        raise HTTPException(status_code=403, detail="Permission restricted to COMMAND.")
    
    try:
        stats = GeoIntelligenceService.get_audit_stats()
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "audit_report": stats
        }
    except Exception as e:
        logger.error(f"Error generating audit report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal error in report generation.")

@app.post("/calculate")
async def calculate(request: GeoRequest, user: dict = Depends(get_api_key)):
    try:
        result = GeoIntelligenceService.process_calculation(
            request.origin, request.target, request.radius
        )
        logger.info(f"CALC_UNITARY | Agent: {user['owner']} | Role: {user['role']} | Result: {result['message']}")
        
        return {"status": "success", "agent": user['owner'], "data": result}
    except Exception as e:
        logger.error(f"Erro tático por {user['owner']}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
@app.post("/calculate/batch")
async def calculate_batch(
    lat: float = Form(...),
    lon: float = Form(...),
    radius: float = Form(5.0),
    file: UploadFile = File(...),
    user: dict = Depends(get_api_key)
):
    try:
        content = await file.read()
        csv_text = content.decode('utf-8')
        origin = {"lat": lat, "lon": lon}
        
        batch_result = GeoIntelligenceService.process_batch_csv(
            csv_text, origin, radius, f"{user['role']} ({user['owner']})"
        )
        logger.info(f"BATCH_OPERATION | Agent: {user['owner']} | Role: {user['role']} | Result: Batch processed")

        return {"status": "success", "mission_report": batch_result}
    except Exception as e:
        logger.error(f"Falha em lote por {user['owner']}: {str(e)}")
        raise HTTPException(status_code=400, detail="Error processing CSV file.")