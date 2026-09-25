from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_container, get_current_credential
from src.api.schemas import KeyGenerationRequest
from src.application.errors import AccessDenied
from src.bootstrap import Container
from src.domain import Credential

router = APIRouter(prefix="/admin")


@router.post("/generate-key")
async def generate_new_key(
    request: KeyGenerationRequest,
    user: Credential = Depends(get_current_credential),
    container: Container = Depends(get_container),
):
    credential = container.access_control.issue_key(
        issuer=user,
        role=request.role,
        owner_name=request.owner_name,
        expires_in_days=request.expires_in_days,
    )
    return {
        "status": "key_generated",
        "api_key": credential.key,
        "role": credential.role,
        "expires_at": credential.expires_at,
    }


@router.get("/stats")
async def get_system_stats(
    user: Credential = Depends(get_current_credential),
    container: Container = Depends(get_container),
):
    try:
        stats = container.audit_report.generate(requester=user)
    except AccessDenied:
        raise
    except Exception as e:
        container.audit_log.error(f"Error generating audit report: {e}")
        raise HTTPException(status_code=500, detail="Internal error in report generation.")

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "audit_report": stats,
    }
