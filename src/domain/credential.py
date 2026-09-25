from dataclasses import dataclass

COMMAND_ROLE = "COMMAND"
DEFAULT_AGENT_NAME = "MASTER_SYSTEM"


@dataclass(frozen=True)
class Credential:
    """API key and the identity it grants.

    The bootstrap COMMAND key has no owner, issuer or expiration.
    """

    key: str
    role: str
    owner: str | None = None
    issuer: str | None = None
    created_at: str = "static"
    expires_at: str | None = None

    @property
    def is_command(self) -> bool:
        return self.role == COMMAND_ROLE

    @property
    def agent_name(self) -> str:
        """Name recorded in the audit log for operations performed with this key."""
        return self.owner if self.owner is not None else DEFAULT_AGENT_NAME
