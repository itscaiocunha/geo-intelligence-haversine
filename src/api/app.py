from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.routes import admin, geo
from src.application.errors import AccessDenied
from src.bootstrap import build_container
from src.infrastructure.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API with its own dependency container. Defaults to settings from the environment."""
    container = build_container(settings or Settings.from_env())

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        container.audit_log.close()

    app = FastAPI(title="Tactical Geo-Int API", version="1.0.0", lifespan=lifespan)
    app.state.container = container
    app.add_exception_handler(AccessDenied, _access_denied_handler)
    app.include_router(admin.router)
    app.include_router(geo.router)
    return app


async def _access_denied_handler(_: Request, exc: AccessDenied) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})
