from fastapi import Request
import logging
import time

logger = logging.getLogger(__name__)


async def log_requests(request: Request, call_next):
    """Log all requests with timing information."""
    start_time = time.time()

    # Log request with auth header info
    auth_header = request.headers.get("Authorization", "Not present")
    auth_info = f"Bearer token present" if auth_header.startswith("Bearer ") else f"Auth header: {auth_header[:50]}"
    logger.info(f"Request: {request.method} {request.url.path} - {auth_info}")

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    logger.info(
        f"Response: {request.method} {request.url.path} - "
        f"Status: {response.status_code} - Duration: {duration:.3f}s"
    )

    return response
