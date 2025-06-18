import httpx
import json
from typing import Optional
from config import config, logger
from utils import mask_key
from .query import ListModelsResponse

class ListModelsHandler:
    def __init__(self, http_client: httpx.AsyncClient):
        self._client = http_client

    async def handle(self) -> ListModelsResponse:
        try:
            response = await self._client.get(
                f"{config['openrouter']['base_url']}/models",
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return ListModelsResponse(data=response.json().get("data", []))
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list models: {e.response.text}")
            raise
