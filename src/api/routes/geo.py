from dataclasses import asdict

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.api.dependencies import get_container, get_current_credential
from src.api.schemas import GeoRequest
from src.bootstrap import Container
from src.domain import Coordinate, Credential

router = APIRouter()


@router.post("/calculate")
async def calculate(
    request: GeoRequest,
    user: Credential = Depends(get_current_credential),
    container: Container = Depends(get_container),
):
    try:
        analysis = container.geo_analysis.analyze_target(
            origin=Coordinate(request.origin["lat"], request.origin["lon"]),
            target=Coordinate(request.target["lat"], request.target["lon"]),
            radius=request.radius,
            agent=user,
        )
    except Exception as e:
        container.audit_log.error(f"Erro tático por {user.agent_name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "success", "agent": user.agent_name, "data": asdict(analysis)}


@router.post("/calculate/batch")
async def calculate_batch(
    lat: float = Form(...),
    lon: float = Form(...),
    radius: float = Form(5.0),
    file: UploadFile = File(...),
    user: Credential = Depends(get_current_credential),
    container: Container = Depends(get_container),
):
    try:
        csv_text = (await file.read()).decode("utf-8")
        report = container.geo_analysis.analyze_batch(
            csv_content=csv_text,
            origin=Coordinate(lat, lon),
            radius=radius,
            agent=user,
        )
    except Exception as e:
        container.audit_log.error(f"Falha em lote por {user.agent_name}: {e}")
        raise HTTPException(status_code=400, detail="Error processing CSV file.")

    return {"status": "success", "mission_report": asdict(report)}
