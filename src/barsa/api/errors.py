"""Centralized API error handling and exception handlers."""

import logging
from datetime import UTC, datetime

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from barsa.core.exceptions import BarsaError
from barsa.models.api import ErrorResponse

logger = logging.getLogger("barsa.api.errors")


def register_error_handlers(app: FastAPI) -> None:
    """Register centralized error handlers on the FastAPI application instance."""

    @app.exception_handler(BarsaError)
    async def barsa_error_handler(request: Request, exc: BarsaError) -> JSONResponse:
        logger.warning(
            "Barsa domain error: [%s] %s on path %s",
            exc.code,
            exc.message,
            request.url.path,
            extra={"error_code": exc.code, "details": exc.details},
        )
        response_model = ErrorResponse(
            error=exc.message,
            code=exc.code,
            status_code=exc.status_code,
            details=exc.details,
            timestamp=datetime.now(UTC),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=response_model.model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info(
            "Request validation failed on path %s: %s",
            request.url.path,
            exc.errors(),
        )
        response_model = ErrorResponse(
            error="Request validation failed",
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"errors": exc.errors()},
            timestamp=datetime.now(UTC),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response_model.model_dump(mode="json"),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        logger.info(
            "HTTP %d error on path %s: %s",
            exc.status_code,
            request.url.path,
            exc.detail,
        )
        response_model = ErrorResponse(
            error=str(exc.detail),
            code=f"HTTP_{exc.status_code}",
            status_code=exc.status_code,
            details={},
            timestamp=datetime.now(UTC),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=response_model.model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception processing request to %s: %s",
            request.url.path,
            str(exc),
        )
        response_model = ErrorResponse(
            error="An unexpected internal server error occurred.",
            code="INTERNAL_SERVER_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={},
            timestamp=datetime.now(UTC),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_model.model_dump(mode="json"),
        )
