"""Interfaces the application layer depends on; implemented in `src.infrastructure`."""

from collections.abc import Iterable
from typing import Protocol

from src.domain import Credential


class CredentialRepository(Protocol):
    def get(self, key: str) -> Credential | None: ...

    def add(self, credential: Credential) -> None: ...


class AuditLog(Protocol):
    """Append-only operation trail, readable back for audit reports."""

    def info(self, message: str) -> None: ...

    def warning(self, message: str) -> None: ...

    def error(self, message: str) -> None: ...

    def entries(self) -> Iterable[str] | None:
        """Raw log lines, or None if nothing has ever been recorded."""
        ...
