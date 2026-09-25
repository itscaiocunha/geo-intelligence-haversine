import secrets
from collections.abc import Callable
from datetime import datetime, timedelta

from src.application.errors import InsufficientPermissions, InvalidCredentials, MissingCredentials
from src.application.ports import AuditLog, CredentialRepository
from src.domain import Credential


class AccessControlService:
    """Authenticates API keys and issues new role-scoped keys."""

    def __init__(
        self,
        repository: CredentialRepository,
        audit_log: AuditLog,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._repository = repository
        self._audit = audit_log
        self._clock = clock

    def authenticate(self, api_key: str | None) -> Credential:
        if not api_key:
            self._audit.warning("ACESSO NEGADO: Tentativa de acesso sem credenciais.")
            raise MissingCredentials("Access Denied: Missing Credentials")

        credential = self._repository.get(api_key)
        if credential is None:
            self._audit.warning("ACESSO NEGADO: Chave inválida detectada.")
            raise InvalidCredentials("Access Denied: Invalid Credentials")
        return credential

    def issue_key(self, issuer: Credential, role: str, owner_name: str, expires_in_days: int) -> Credential:
        if not issuer.is_command:
            raise InsufficientPermissions("Insufficient permissions.")

        now = self._clock()
        credential = Credential(
            key=f"geo_{secrets.token_urlsafe(32)}",
            role=role,
            owner=owner_name,
            issuer=issuer.agent_name,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(days=expires_in_days)).isoformat(),
        )
        self._repository.add(credential)

        self._audit.info(f"KEY_GEN | Issuer: {credential.issuer} | Recipient: {owner_name} | Role: {role}")
        return credential
