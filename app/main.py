from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import router as v1_router
from app.config.settings import get_settings
from app.middleware.request_id import RequestIDMiddleware
from app.schemas.error import ErrorResponse
from app.services.classifier import TicketSortingService
from app.utils.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    service = TicketSortingService(settings)
    app.state.ticket_service = service
    service.warmup()
    logger.info("application_started", extra={"environment": settings.environment})
    yield
    logger.info("application_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="CPU-friendly fintech support ticket classifier for QueueStorm.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Compatibility for tests that instantiate TestClient without lifespan context.
    app.state.ticket_service = TicketSortingService(settings)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        error = ErrorResponse(
            error="validation_error",
            detail=exc.errors(),
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error.model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("unhandled_exception", extra={"request_id": request_id})
        error = ErrorResponse(
            error="internal_server_error",
            detail="Unexpected server error",
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error.model_dump(),
        )

    @app.get("/", tags=["service"])
    def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "status": "online",
            "docs": "/docs",
            "health": "/health",
            "sort_ticket": "/sort-ticket",
        }

    app.include_router(v1_router, prefix=settings.api_prefix)
    # Root compatibility endpoints for hackathon judges that call exact paths.
    app.include_router(v1_router)
    return app


app = create_app()
