from datetime import datetime

import pytest

from src.application.access_control import AccessControlService
from src.application.audit_report import NO_AUDIT_DATA, AuditReportService, build_audit_report
from src.application.errors import InsufficientPermissions, InvalidCredentials, MissingCredentials
from src.application.geo_analysis import GeoAnalysisService
from src.domain import Coordinate, Credential
from src.infrastructure.credential_store import InMemoryCredentialRepository

COMMAND = Credential(key="cmd", role="COMMAND")
OPERATOR = Credential(key="op", role="OPERATOR", owner="Agent-07")
ORIGIN = Coordinate(-23.5505, -46.6333)


class FakeAuditLog:
    def __init__(self, lines=None):
        self.records = []
        self._lines = lines

    def info(self, message):
        self.records.append(("INFO", message))

    def warning(self, message):
        self.records.append(("WARNING", message))

    def error(self, message):
        self.records.append(("ERROR", message))

    def entries(self):
        return self._lines


# --- access control ---

def make_access_control(audit=None):
    repository = InMemoryCredentialRepository()
    repository.add(COMMAND)
    return AccessControlService(repository, audit or FakeAuditLog(), clock=lambda: datetime(2026, 1, 1))


def test_authenticate_rejects_missing_and_unknown_keys():
    audit = FakeAuditLog()
    service = make_access_control(audit)

    with pytest.raises(MissingCredentials):
        service.authenticate(None)
    with pytest.raises(InvalidCredentials):
        service.authenticate("unknown")
    assert [level for level, _ in audit.records] == ["WARNING", "WARNING"]


def test_issued_key_authenticates_with_its_role_and_expiration():
    audit = FakeAuditLog()
    service = make_access_control(audit)

    issued = service.issue_key(COMMAND, role="OPERATOR", owner_name="Agent-07", expires_in_days=30)

    assert issued.key.startswith("geo_")
    assert issued.issuer == "MASTER_SYSTEM"
    assert issued.expires_at == "2026-01-31T00:00:00"
    assert service.authenticate(issued.key) == issued
    assert audit.records[-1] == ("INFO", "KEY_GEN | Issuer: MASTER_SYSTEM | Recipient: Agent-07 | Role: OPERATOR")


def test_only_command_can_issue_keys():
    with pytest.raises(InsufficientPermissions):
        make_access_control().issue_key(OPERATOR, role="OPERATOR", owner_name="x", expires_in_days=1)


# --- geo analysis ---

def test_analyze_target_flags_perimeter_violation():
    audit = FakeAuditLog()
    analysis = GeoAnalysisService(audit).analyze_target(
        Coordinate(-15.7942, -47.8822), Coordinate(-15.8010, -47.8920), radius=5.0, agent=OPERATOR
    )

    assert (analysis.distance_km, analysis.alert, analysis.message) == (1.29, True, "WARNING: Perimeter Violated!")
    assert audit.records == [
        ("INFO", "CALC_UNITARY | Agent: Agent-07 | Role: OPERATOR | Result: WARNING: Perimeter Violated!")
    ]


def test_analyze_batch_skips_invalid_rows():
    csv_content = "name,lat,lon\nA,abc,1\nB,95,1\nC,-23.55,-46.63\nD,1\n"
    report = GeoAnalysisService(FakeAuditLog()).analyze_batch(csv_content, ORIGIN, radius=5.0, agent=OPERATOR)

    assert report.summary.total_processed == 1
    assert report.details[0].target == "C"


def test_analyze_batch_uses_fallback_name_and_logs_once():
    audit = FakeAuditLog()
    report = GeoAnalysisService(audit).analyze_batch("lat,lon\n-23.56,-46.64\n", ORIGIN, radius=5.0, agent=OPERATOR)

    assert report.details[0].target == "Alvo Desconhecido"
    assert report.summary.violations_detected == 1
    assert len(audit.records) == 1
    assert audit.records[0][1].endswith("| Targets: 1 | Violations: 1")


# --- audit report ---

LOG_LINES = [
    "t - INFO - [GEO-INT] - Audit system initialized and logging started.\n",
    "t - WARNING - [GEO-INT] - ACESSO NEGADO: Chave inválida detectada.\n",
    "t - INFO - [GEO-INT] - KEY_GEN | Issuer: MASTER_SYSTEM | Recipient: Agent-07 | Role: OPERATOR\n",
    "t - INFO - [GEO-INT] - CALC_UNITARY | Agent: Agent-07 | Role: OPERATOR | Result: WARNING: Perimeter Violated!\n",
    "t - INFO - [GEO-INT] - CALC_UNITARY | Agent: Agent-07 | Role: OPERATOR | Result: Area Secure.\n",
    "t - INFO - [GEO-INT] - BATCH_OPERATION | Agent: Agent-07 | Role: OPERATOR | Origin: {} | Targets: 3 | Violations: 2\n",
    "t - INFO - [GEO-INT] - Batch processed by OPERATOR (Agent-09) | Violations: 4\n",
]


def test_build_audit_report_aggregates_by_agent():
    report = build_audit_report(LOG_LINES)

    assert report["global_summary"] == {
        "total_entries": 7,
        "total_violations": 7,
        "operation_types": {"UNITARY": 2, "BATCH": 2, "KEY_GEN": 1},
    }
    assert report["agents_detail"]["Agent-07"] == {
        "total_ops": 3, "unitary_calcs": 2, "batch_calcs": 1, "keys_generated": 0, "violations_found": 3,
    }
    assert report["agents_detail"]["MASTER_SYSTEM"]["keys_generated"] == 1
    assert report["agents_detail"]["Agent-09"]["violations_found"] == 4


def test_audit_report_requires_command_role():
    audit = FakeAuditLog(LOG_LINES)
    with pytest.raises(InsufficientPermissions):
        AuditReportService(audit).generate(OPERATOR)
    assert audit.records[0][0] == "WARNING"


def test_audit_report_without_log():
    assert AuditReportService(FakeAuditLog(lines=None)).generate(COMMAND) == {"message": NO_AUDIT_DATA}
