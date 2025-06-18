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
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.templating import Jinja2Templates
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.shared.config import config, logger

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")
from src.shared.utils import get_local_ip
from src.shared.metrics import (
    CPU_USAGE, MEMORY_USAGE, ACTIVE_KEYS, COOLDOWN_KEYS, TOKENS_SENT, TOKENS_RECEIVED
)
from src.services.key_manager import KeyManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan resources."""
    proxy_url = config["requestProxy"].get("url") if config["requestProxy"].get("enabled") else None
    app.state.http_client = httpx.AsyncClient(timeout=600.0, proxy=proxy_url)
    app.state.key_manager = KeyManager(
        keys=config["openrouter"]["keys"],
        cooldown_seconds=config["openrouter"]["rate_limit_cooldown"],
        strategy=config["openrouter"]["key_selection_strategy"],
        opts=config["openrouter"]["key_selection_opts"],
    )
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

# Include feature routers
from src.features.get_next_key.endpoints import router as get_next_key_router
from src.features.disable_key.endpoints import router as disable_key_router
from src.features.kms_metrics.endpoints import router as kms_metrics_router
from src.features.list_models.endpoints import router as list_models_router
from src.features.proxy_chat.endpoints import router as proxy_chat_router

app.include_router(list_models_router, prefix="/api/v1", tags=["Proxy"])
app.include_router(proxy_chat_router, prefix="/api/v1", tags=["Proxy"])
app.include_router(get_next_key_router, prefix="/api/v1/kms", tags=["KMS"])
app.include_router(disable_key_router, prefix="/api/v1/kms", tags=["KMS"])
app.include_router(kms_metrics_router, prefix="/api/v1/kms", tags=["KMS"])

# Metrics endpoint with HTML dashboard
@app.get("/metrics", response_class=HTMLResponse)
async def metrics(request: Request):
    """Returns metrics in HTML table format by default"""
    # Update system metrics if enabled and psutil available
    if config["server"].get("enable_system_metrics", False):
        if PSUTIL_AVAILABLE:
            CPU_USAGE.set(psutil.cpu_percent())
            MEMORY_USAGE.set(psutil.virtual_memory().percent)
        else:
            logger.warning("System metrics enabled but psutil not installed. Run 'pip install psutil' to enable CPU/memory monitoring.")
    
    # Get local Prometheus metrics
    metrics_data = generate_latest().decode('utf-8')
    
    # Update KMS metrics directly from the state manager
    key_manager: KeyManager = request.app.state.key_manager
    key_manager.update_metrics()

    # Re-generate metrics data after update
    metrics_data = generate_latest().decode('utf-8')
    
    # HTML template
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>OpenRouter Proxy Metrics</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
            .metrics-table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .metrics-table th, .metrics-table td {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
            }}
            .metrics-table th {{
                background-color: #f8f9fa;
                position: sticky;
                top: 0;
            }}
            .metrics-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .metrics-table tr:hover {{ background-color: #f1f1f1; }}
            .metric-value {{ font-family: monospace; }}
            .section {{ margin-bottom: 30px; }}
            .raw-link {{ 
                display: inline-block;
                margin-top: 20px;
                color: #666;
                font-size: 0.9em;
            }}
        </style>
    </head>
    <body>
        <h1>OpenRouter Proxy Metrics</h1>
        
        <div class="section">
            <h2>System Resources</h2>
            <table class="metrics-table">
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>CPU Usage</td><td class="metric-value">{CPU_USAGE._value.get() if PSUTIL_AVAILABLE else 'N/A'}%</td></tr>
                <tr><td>Memory Usage</td><td class="metric-value">{MEMORY_USAGE._value.get() if PSUTIL_AVAILABLE else 'N/A'}%</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h2>API Keys</h2>
            <table class="metrics-table">
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Active Keys</td><td class="metric-value">{ACTIVE_KEYS._value.get()}</td></tr>
                <tr><td>Keys in Cooldown</td><td class="metric-value">{COOLDOWN_KEYS._value.get()}</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Token Statistics</h2>
            <table class="metrics-table">
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Tokens Sent</td><td class="metric-value">{TOKENS_SENT._value.get()}</td></tr>
                <tr><td>Tokens Received</td><td class="metric-value">{TOKENS_RECEIVED._value.get()}</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h2>All Prometheus Metrics</h2>
            <pre>{metrics_data}</pre>
        </div>
        
        <a href="/metrics/raw" class="raw-link">View raw Prometheus format</a>
    </body>
    </html>
    """
    
    # Parse and add all Prometheus metrics
    current_type = ""
    for line in metrics_data.split('\n'):
        if line.startswith('# TYPE'):
            current_type = line.split(' ')[3]
        elif line and not line.startswith('#'):
            parts = line.split(' ')
            if len(parts) >= 2:
                html += f"""
                <tr>
                    <td>{parts[0]}</td>
                    <td class="metric-value">{' '.join(parts[1:])}</td>
                    <td>{current_type}</td>
                </tr>
                """
    
    html += """
            </table>
        </div>
        
        <a href="/metrics/raw" class="raw-link">View raw Prometheus format</a>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# Raw metrics endpoint
@app.get("/metrics/raw")
async def metrics_raw():
    """Returns raw Prometheus format"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# Request ID middleware
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

app.add_middleware(RequestIDMiddleware)

# Request timing middleware
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Remove duplicate headers that might be added by downstream
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

# Entry point
import multiprocessing
import subprocess
import time

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
    
    # HTTP access logs configuration
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
