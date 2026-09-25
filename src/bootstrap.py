"""Composition root: the only place where concrete adapters are wired into the use cases."""

from dataclasses import dataclass

from src.application.access_control import AccessControlService
from src.application.audit_report import AuditReportService
from src.application.geo_analysis import GeoAnalysisService
from src.domain import COMMAND_ROLE, Credential
from src.infrastructure.audit_log import FileAuditLog
from src.infrastructure.config import Settings
from src.infrastructure.credential_store import InMemoryCredentialRepository


@dataclass(frozen=True)
class Container:
    audit_log: FileAuditLog
    access_control: AccessControlService
    geo_analysis: GeoAnalysisService
    audit_report: AuditReportService


def build_container(settings: Settings) -> Container:
    audit_log = FileAuditLog(settings.audit_log_path)

    credentials = InMemoryCredentialRepository()
    if settings.command_key:
        credentials.add(Credential(key=settings.command_key, role=COMMAND_ROLE))
    else:
        print("CRITICAL: API_KEY_COMMAND not found in environment!")

    return Container(
        audit_log=audit_log,
        access_control=AccessControlService(credentials, audit_log),
        geo_analysis=GeoAnalysisService(audit_log),
        audit_report=AuditReportService(audit_log),
    )
