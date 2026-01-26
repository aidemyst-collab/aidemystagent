from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    logger.error(
        f"HTTP Exception: {exc.status_code} - {exc.detail} - Path: {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "status_code": exc.status_code,
                "path": str(request.url.path),
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.error(f"Validation Error: {exc.errors()} - Path: {request.url.path}")

    # Convert errors to JSON-serializable format
    errors = []
    for error in exc.errors():
        serializable_error = {
            "loc": error.get("loc"),
            "msg": str(error.get("msg", "")),
            "type": error.get("type"),
        }
        # Convert any non-serializable input to string
        if "input" in error:
            try:
                import json
                json.dumps(error["input"])
                serializable_error["input"] = error["input"]
            except (TypeError, ValueError):
                serializable_error["input"] = str(error["input"])
        errors.append(serializable_error)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Validation error",
                "details": errors,
                "path": str(request.url.path),
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    logger.error(
        f"Unhandled Exception: {str(exc)} - Path: {request.url.path}\n{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "Internal server error",
                "path": str(request.url.path),
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
    )
