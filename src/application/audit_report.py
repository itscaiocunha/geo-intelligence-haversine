"""Audit report built by parsing the operation log.

Besides the current line formats (`CALC_UNITARY`, `BATCH_OPERATION`, `KEY_GEN`), the parser
still understands the legacy `Batch processed by ROLE (owner)` lines of older log files.
"""

from collections.abc import Iterable

from src.application.errors import InsufficientPermissions
from src.application.ports import AuditLog
from src.domain import Credential

NO_AUDIT_DATA = "Nenhum dado de auditoria disponível."
LEGACY_BATCH_MARKER = "Batch processed by "


class AuditReportService:
    def __init__(self, audit_log: AuditLog) -> None:
        self._audit = audit_log

    def generate(self, requester: Credential) -> dict:
        if not requester.is_command:
            self._audit.warning("ACCESS DENIED: Operator attempted to access admin statistics.")
            raise InsufficientPermissions("Permission restricted to COMMAND.")

        entries = self._audit.entries()
        if entries is None:
            return {"message": NO_AUDIT_DATA}
        return build_audit_report(entries)


def build_audit_report(lines: Iterable[str]) -> dict:
    """Aggregate log lines into global counters and per-agent activity."""
    summary = {
        "total_entries": 0,
        "total_violations": 0,
        "operation_types": {"UNITARY": 0, "BATCH": 0, "KEY_GEN": 0},
    }
    agents: dict[str, dict[str, int]] = {}

    for line in lines:
        summary["total_entries"] += 1

        agent_name = _extract_agent(line)
        if not agent_name:
            continue

        agent = agents.setdefault(agent_name, _empty_agent_stats())
        agent["total_ops"] += 1

        if "CALC_UNITARY" in line:
            agent["unitary_calcs"] += 1
            summary["operation_types"]["UNITARY"] += 1
            violations = 1 if "Perimeter Violated!" in line else 0
        elif "BATCH_OPERATION" in line or LEGACY_BATCH_MARKER.strip() in line:
            agent["batch_calcs"] += 1
            summary["operation_types"]["BATCH"] += 1
            violations = int(line.split("Violations: ")[1].strip()) if "Violations: " in line else 0
        elif "KEY_GEN" in line:
            agent["keys_generated"] += 1
            summary["operation_types"]["KEY_GEN"] += 1
            violations = 0
        else:
            violations = 0

        agent["violations_found"] += violations
        summary["total_violations"] += violations

    return {"global_summary": summary, "agents_detail": agents}


def _extract_agent(line: str) -> str | None:
    if "Agent: " in line:
        return line.split("Agent: ")[1].split(" |")[0]
    if "Issuer: " in line:
        return line.split("Issuer: ")[1].split(" |")[0]
    if LEGACY_BATCH_MARKER in line:
        return line.split("(")[1].split(")")[0] if "(" in line else "SYSTEM"
    return None


def _empty_agent_stats() -> dict[str, int]:
    return {
        "total_ops": 0,
        "unitary_calcs": 0,
        "batch_calcs": 0,
        "keys_generated": 0,
        "violations_found": 0,
    }
