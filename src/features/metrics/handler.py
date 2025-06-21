from fastapi import Request, Depends
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.services.key_manager import KeyManager
from src.shared.dependencies import get_key_manager
from src.shared.metrics import ACTIVE_KEYS, COOLDOWN_KEYS

# The templates directory is relative to the execution root, not this file.
templates = Jinja2Templates(directory="templates")

class MetricsHandler:
    """Handles the logic for serving monitoring metrics."""

    def __init__(self, key_manager: KeyManager = Depends(get_key_manager)):
        self._key_manager = key_manager

    def get_metrics_dashboard(self, request: Request) -> HTMLResponse:
        """Generates the HTML dashboard for metrics."""
        self._key_manager.update_metrics()
        metrics_data = generate_latest().decode('utf-8')

        context = {
            "request": request,
            "active_keys": int(ACTIVE_KEYS._value.get()),
            "cooldown_keys": int(COOLDOWN_KEYS._value.get()),
            "raw_metrics": metrics_data
        }
        return templates.TemplateResponse("metrics.html", context)

    def get_raw_metrics(self) -> Response:
        """Returns raw metrics in Prometheus format."""
        self._key_manager.update_metrics()
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
