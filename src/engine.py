import math
from dataclasses import dataclass
from typing import Union
import os
import logging

os.makedirs("data", exist_ok=True)

file_handler = logging.FileHandler("data/operation.log", mode='a', encoding='utf-8', delay=False)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [GEO-INT] - %(message)s',
    handlers=[
        file_handler,
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("BOOT: Geo-Intelligence System Initiated.")

# Average radius of the Earth in kilometers (Reference: WGS-84)
EARTH_RADIUS_KM = 6371.0

@dataclass
class Coordinate:
    lat: float
    lon: float

    def __post_init__(self):
        """Tactical validation: Ensures coordinates are physically real."""
        if not -90 <= self.lat <= 90:
            raise ValueError(f"Invalid latitude: {self.lat}. Must be between -90 and 90.")
        if not -180 <= self.lon <= 180:
            raise ValueError(f"Invalid longitude: {self.lon}. Must be between -180 and 180.")

class HaversineEngine:
    """Engine for calculating operations in geospatial intelligence."""

    @staticmethod
    def calculate_distance(origin: Coordinate, destination: Coordinate, unit: str = "KM") -> float:
        logger.info(f"Starting calculation: Origin({origin.lat}, {origin.lon}) -> Destination({destination.lat}, {destination.lon})")
        
        try:
            """
            Calculates the great circle distance between two points using Haversine.

            Args:
                origin (Coordinate): Object containing lat/lon origin.
                destination (Coordinate): Object containing lat/lon destination.
                unit (str): Output unit ('KM', 'M', 'NM'). Default is 'KM'.

            Returns:
                float: Linear distance in the specified unit.

            Raises:
                ValueError: If the coordinates are invalid.
            """

            # Conversion to Radians - Fundamental for spherical trigonometry
            phi1, phi2 = math.radians(origin.lat), math.radians(destination.lat)
            delta_phi = math.radians(destination.lat - origin.lat)
            delta_lambda = math.radians(destination.lon - origin.lon)

            # Application of the Haversine Formula
            a = (math.sin(delta_phi / 2) ** 2 +
                math.cos(phi1) * math.cos(phi2) *
                math.sin(delta_lambda / 2) ** 2)
            
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            
            distance = EARTH_RADIUS_KM * c

            # Unit conversion if necessary.
            if unit.upper() == "NM":  # Nautical Miles (Marine/Air Standard)
                return distance * 0.539957
            elif unit.upper() == "M":   # Meters
                return distance * 1000
            
            logger.info(f"Calculation completed successfully: {distance:.2f} {unit}")
            return distance
      
        except Exception as e:
              logger.error(f"Failed in geospatial operation: {str(e)}")
              raise
    
    @staticmethod
    def is_within_radius(origin: Coordinate, target: Coordinate, radius: float) -> bool:
        """
        Checks if a target has breached a security perimeter (Geofencing)..

        Args:
            origin (Coordinate): Center of the perimeter.
            target (Coordinate): Current position of the target.
            radius (float): Surveillance radius in kilometers.

        Returns:
            bool: True if the target is within the radius, False otherwise.
        """
        distance = HaversineEngine.calculate_distance(origin, target)
        within = distance <= radius
        
        if within:
            logger.warning(f"PERIMETER ALERT: Target detected at {distance:.2f}km from the base!")
        else:
            logger.info(f"Monitoring: Target out of range ({distance:.2f}km).")

        return within