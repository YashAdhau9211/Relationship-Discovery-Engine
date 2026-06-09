from contextlib import asynccontextmanager

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import api_router
from app.core.config import Settings, get_settings
from app.core.errors import DomainError
from app.db.schema import bootstrap_schema
from app.schemas.common import ApiError, ErrorDetail


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    logging.basicConfig(level=app_settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if app_settings.bootstrap_schema:
            bootstrap_schema(app_settings)
        yield

    app = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        description="Backend-first RDNAE Feature 1 API.",
        lifespan=lifespan,
        responses={
            400: {"model": ApiError},
            404: {"model": ApiError},
            500: {"model": ApiError},
        },
    )
    app.state.settings = app_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        error = ApiError(error=ErrorDetail(code=exc.code, message=exc.message, details=exc.details))
        return JSONResponse(status_code=exc.status_code, content=error.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        error = ApiError(
            error=ErrorDetail(
                code="validation_error",
                message="Request validation failed.",
                details={"errors": exc.errors()},
            )
        )
        return JSONResponse(status_code=422, content=error.model_dump())

    @app.exception_handler(HTTPException)
    async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
        error = ApiError(
            error=ErrorDetail(
                code="http_error",
                message=str(exc.detail),
                details={"status_code": exc.status_code},
            )
        )
        return JSONResponse(status_code=exc.status_code, content=error.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        error = ApiError(
            error=ErrorDetail(
                code="internal_error",
                message="Unexpected backend error.",
                details={"type": exc.__class__.__name__},
            )
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    app.include_router(api_router, prefix=app_settings.api_prefix)
    return app


app = create_app()
