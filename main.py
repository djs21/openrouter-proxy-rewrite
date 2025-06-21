#!/usr/bin/env python3
"""
OpenRouter API Proxy
Proxies requests to OpenRouter API and rotates API keys to bypass rate limits.
"""

import sys
import uuid
import time
from contextlib import asynccontextmanager

import httpx
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.templating import Jinja2Templates
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from config import config, logger
from utils import get_local_ip
from src.services.key_manager import KeyManager
from src.services.model_filter_service import ModelFilterService

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")
from metrics import (
    ACTIVE_KEYS, COOLDOWN_KEYS
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan resources."""
    proxy_url = config["requestProxy"].get("url") if config["requestProxy"].get("enabled") else None
    if proxy_url:
        app.state.http_client = httpx.AsyncClient(timeout=600.0, proxies={"http://": proxy_url, "https://": proxy_url})
    else:
        app.state.http_client = httpx.AsyncClient(timeout=600.0)

    app.state.key_manager = KeyManager(
        keys=config["openrouter"]["keys"],
        cooldown_seconds=config["openrouter"]["rate_limit_cooldown"],
        strategy=config["openrouter"]["key_selection_strategy"],
        opts=config["openrouter"]["key_selection_opts"],
    )

    app.state.model_filter_service = ModelFilterService(http_client=app.state.http_client)

    logger.info("Application startup complete")
    yield
    await app.state.http_client.aclose()
    logger.info("Application shutdown complete")

app = FastAPI(
    title="OpenRouter API Proxy",
    description="Proxies requests to OpenRouter API and rotates API keys to bypass rate limits",
    version="1.0.0",
    lifespan=lifespan,
)

from fastapi import Depends
from src.features.list_models.endpoints import router as list_models_router
from src.features.proxy_chat.endpoints import router as proxy_chat_router
from src.features.health_check.endpoints import router as health_check_router
from src.features.metrics.endpoints import router as metrics_router
from utils import verify_access_key

app.include_router(
    list_models_router,
    prefix="/api/v1",
    tags=["Proxy"]
)
app.include_router(
    proxy_chat_router,
    prefix="/api/v1",
    dependencies=[Depends(verify_access_key)],
    tags=["Proxy"]
)
app.include_router(health_check_router, tags=["Monitoring"])
app.include_router(metrics_router)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

app.add_middleware(RequestIDMiddleware)

@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    if "date" in response.headers:
        del response.headers["date"]

    logger.info(
        "Request completed",
        extra={
            "req_id": request.state.request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_sec": round(process_time, 4)
        }
    )
    return response

if __name__ == "__main__":
    if not config["openrouter"]["keys"]:
        logger.error("No OpenRouter API keys found in config.yml or OPENROUTER_KEYS environment variable. Exiting.")
        sys.exit(1)

    host = config["server"]["host"]
    port = config["server"]["port"]

    display_host = get_local_ip() if host == "0.0.0.0" else host
    logger.warning("Starting OpenRouter Proxy on %s:%s", host, port)
    logger.warning("API URL: http://%s:%s/api/v1", display_host, port)
    logger.warning("Metrics: http://%s:%s/metrics", display_host, port)

    log_config = uvicorn.config.LOGGING_CONFIG
    http_log_level = config["server"].get("http_log_level", "INFO").upper()
    log_config["loggers"]["uvicorn.access"]["level"] = http_log_level

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config=log_config,
        timeout_graceful_shutdown=30,
        server_header=False
    )
