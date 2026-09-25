from fastapi import Depends, Request, Security
from fastapi.security.api_key import APIKeyHeader

from src.bootstrap import Container
from src.domain import Credential

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def get_container(request: Request) -> Container:
    return request.app.state.container


async def get_current_credential(
    api_key: str | None = Security(api_key_header),
    container: Container = Depends(get_container),
) -> Credential:
    return container.access_control.authenticate(api_key)
