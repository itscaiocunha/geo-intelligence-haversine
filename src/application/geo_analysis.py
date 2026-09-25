import csv
import io
from dataclasses import asdict, dataclass, field

from src.application.ports import AuditLog
from src.domain import Coordinate, Credential, HaversineEngine

PERIMETER_VIOLATED = "WARNING: Perimeter Violated!"
AREA_SECURE = "Area Secure."
UNKNOWN_TARGET = "Alvo Desconhecido"


@dataclass(frozen=True)
class TargetAnalysis:
    distance_km: float
    alert: bool
    message: str


@dataclass(frozen=True)
class BatchTargetResult:
    target: str | None
    distance_km: float
    violation: bool


@dataclass(frozen=True)
class BatchSummary:
    total_processed: int
    violations_detected: int


@dataclass(frozen=True)
class BatchReport:
    summary: BatchSummary
    details: list[BatchTargetResult] = field(default_factory=list)


class GeoAnalysisService:
    """Distance and perimeter analysis for one target or a CSV list of targets."""

    def __init__(self, audit_log: AuditLog) -> None:
        self._audit = audit_log

    def analyze_target(
        self, origin: Coordinate, target: Coordinate, radius: float, agent: Credential
    ) -> TargetAnalysis:
        distance = HaversineEngine.calculate_distance(origin, target)
        alert = distance <= radius
        analysis = TargetAnalysis(
            distance_km=round(distance, 2),
            alert=alert,
            message=PERIMETER_VIOLATED if alert else AREA_SECURE,
        )

        self._audit.info(
            f"CALC_UNITARY | Agent: {agent.agent_name} | Role: {agent.role} | Result: {analysis.message}"
        )
        return analysis

    def analyze_batch(self, csv_content: str, origin: Coordinate, radius: float, agent: Credential) -> BatchReport:
        """Analyze every `name,lat,lon` row; rows with missing or invalid coordinates are skipped."""
        details = []
        for row in csv.DictReader(io.StringIO(csv_content)):
            try:
                target = Coordinate(float(row["lat"]), float(row["lon"]))
            except (ValueError, KeyError, TypeError):
                continue

            distance = HaversineEngine.calculate_distance(origin, target)
            details.append(BatchTargetResult(
                target=row.get("name", UNKNOWN_TARGET),
                distance_km=round(distance, 2),
                violation=distance <= radius,
            ))

        report = BatchReport(
            summary=BatchSummary(
                total_processed=len(details),
                violations_detected=sum(result.violation for result in details),
            ),
            details=details,
        )

        self._audit.info(
            f"BATCH_OPERATION | Agent: {agent.agent_name} | Role: {agent.role} | Origin: {asdict(origin)} | "
            f"Targets: {report.summary.total_processed} | Violations: {report.summary.violations_detected}"
        )
        return report
