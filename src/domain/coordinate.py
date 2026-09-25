from dataclasses import dataclass


@dataclass(frozen=True)
class Coordinate:
    """Geographic point in decimal degrees, validated on creation."""

    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not (-90 <= self.lat <= 90):
            raise ValueError("Latitude deve estar entre -90 e 90.")
        if not (-180 <= self.lon <= 180):
            raise ValueError("Longitude deve estar entre -180 e 180.")
