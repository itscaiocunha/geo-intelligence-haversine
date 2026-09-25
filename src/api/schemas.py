from pydantic import BaseModel


class KeyGenerationRequest(BaseModel):
    role: str = "OPERATOR"
    owner_name: str
    expires_in_days: int = 30


class GeoRequest(BaseModel):
    # Points are plain {"lat", "lon"} mappings; range checks happen in the domain `Coordinate`.
    origin: dict
    target: dict
    radius: float = 5.0
