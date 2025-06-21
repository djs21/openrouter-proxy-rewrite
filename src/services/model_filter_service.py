import time
import httpx
import asyncio
from typing import Set, List, Dict, Any
from src.shared.config import logger

class ModelFilterService:
    """
    A service to fetch, cache, and filter OpenRouter models.
    """
    def __init__(self, http_client: httpx.AsyncClient, cache_ttl_seconds: int = 3600):
        self._client = http_client
        self._cache_ttl = cache_ttl_seconds
        self._all_models: List[Dict[str, Any]] = []
        self._free_model_ids: Set[str] = set()
        self._last_fetch_time: float = 0.0
        self._lock = asyncio.Lock()

    async def _refresh_cache(self) -> None:
        """Fetches the model list and refreshes the cache."""
        logger.info("Refreshing models cache...")
        try:
            response = await self._client.get("https://openrouter.ai/api/v1/models")
            response.raise_for_status()
            models_data = response.json().get("data", [])

            self._all_models = models_data
            self._free_model_ids = {
                m['id'] for m in models_data
                if m.get('id', '').endswith(':free')
            }
            self._last_fetch_time = time.time()
            logger.info(
                "Successfully refreshed models cache. Found %s models (%s free).",
                len(self._all_models), len(self._free_model_ids)
            )
        except httpx.HTTPError as e:
            logger.error("Failed to refresh models cache: %s", e)
            self._last_fetch_time = time.time()

    async def _ensure_cache_is_fresh(self) -> None:
        """Checks if cache is stale and refreshes it if necessary."""
        async with self._lock:
            is_cache_stale = (time.time() - self._last_fetch_time) > self._cache_ttl
            if not self._all_models or is_cache_stale:
                await self._refresh_cache()

    async def get_models(self) -> List[Dict[str, Any]]:
        """Returns the cached list of all models."""
        await self._ensure_cache_is_fresh()
        return self._all_models

    async def get_free_model_ids(self) -> Set[str]:
        """Returns the cached set of free model IDs."""
        await self._ensure_cache_is_fresh()
        return self._free_model_ids

    async def is_model_allowed(self, model_id: str) -> bool:
        """Checks if a given model ID is in the cached list of free models."""
        free_ids = await self.get_free_model_ids()
        return model_id in free_ids
