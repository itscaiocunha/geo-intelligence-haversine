from src.domain import Credential


class InMemoryCredentialRepository:
    """Process-local key store: issued keys are lost when the service restarts."""

    def __init__(self) -> None:
        self._credentials: dict[str, Credential] = {}

    def get(self, key: str) -> Credential | None:
        return self._credentials.get(key)

    def add(self, credential: Credential) -> None:
        self._credentials[credential.key] = credential
