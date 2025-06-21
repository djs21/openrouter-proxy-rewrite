from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response

from .handler import MetricsHandler

router = APIRouter()

@router.get("/metrics", response_class=HTMLResponse, tags=["Monitoring"])
def metrics_dashboard(
    request: Request,
    handler: MetricsHandler = Depends(MetricsHandler)
) -> HTMLResponse:
    """Returns metrics in an HTML dashboard."""
    return handler.get_metrics_dashboard(request)

@router.get("/metrics/raw", tags=["Monitoring"])
def metrics_raw(handler: MetricsHandler = Depends(MetricsHandler)) -> Response:
    """Returns raw Prometheus format metrics."""
    return handler.get_raw_metrics()
