import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from src.shared.config import logger

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Injects a unique request ID into every incoming request for tracing.
    """
    async def dispatch(
        self, request: Request, call_next
    ) -> Response:
        request.state.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

async def add_process_time_header(
    request: Request, call_next
) -> Response:
    """
    Adds a custom X-Process-Time header and logs request completion details.
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # The 'date' header is removed as it is often redundant and inconsistently
    # populated by various components in the proxy chain.
    if "date" in response.headers:
        del response.headers["date"]

    logger.info(
        "Request completed",
        extra={
            "req_id": getattr(request.state, 'request_id', 'N/A'),
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_sec": round(process_time, 4)
        }
    )
    return response
