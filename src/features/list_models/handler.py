import httpx
import json
from typing import Optional
import time
from config import config, logger
from utils import mask_key
from .query import ListModelsResponse

class ListModelsHandler:
    def __init__(self, http_client: httpx.AsyncClient):
        self._client = http_client
        self._last_fetch = 0
        self._cached_response = None

    async def handle(self) -> ListModelsResponse:
        # Use cached response if available and fresh
        current_time = time.time()
        if (self._cached_response and 
            (current_time - self._last_fetch) < config["openrouter"]["cache_ttl"]):
            logger.info("Returning cached models list")
            return self._cached_response

        # Fetch fresh models list
        try:
            response = await self._client.get(
                f"{config['openrouter']['base_url']}/models",
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            models_data = response.json().get("data", [])
            logger.info(f"Fetched {len(models_data)} models from OpenRouter")
            
            # Cache the response
            self._cached_response = ListModelsResponse(data=models_data)
            self._last_fetch = current_time
            return self._cached_response
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text or str(e)
            logger.error(f"Failed to list models: {error_detail}")
            raise
