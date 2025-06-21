import httpx
from fastapi import Depends
from src.shared.dependencies import get_http_client
from src.shared.config import config, logger
from .query import HealthCheckResponse

class HealthCheckHandler:
    def __init__(self, http_client: httpx.AsyncClient = Depends(get_http_client)):
        self._http_client = http_client

    async def handle(self) -> HealthCheckResponse:
        services_status = {}

        # Check OpenRouter API status
        try:
            health_resp = await self._http_client.head(
                f"{config['openrouter']['base_url']}/health",
                timeout=5.0
            )
            services_status["openrouter_api"] = "up" if health_resp.status_code < 500 else "down"
        except Exception as e:
            logger.error("OpenRouter API health check failed: %s", str(e))
            services_status["openrouter_api"] = "down"

        overall_status = "ok" if all(s == "up" for s in services_status.values()) else "error"
        return HealthCheckResponse(status=overall_status, services=services_status)
