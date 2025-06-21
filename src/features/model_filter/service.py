import time
import httpx
import asyncio
from typing import Set
from config import logger

class ModelFilterService:
    """
    A service to fetch, cache, and filter OpenRouter models.
    """
    def __init__(self, http_client: httpx.AsyncClient, cache_ttl_seconds: int = 3600):
        self._client = http_client
        self._cache_ttl = cache_ttl_seconds
        self._free_model_ids: Set[str] = set()
        self._last_fetch_time = 0
        self._lock = asyncio.Lock()

    async def _refresh_cache(self):
        """Fetches the model list and refreshes the set of free model IDs."""
        logger.info("Refreshing free models cache...")
        try:
            response = await self._client.get("https://openrouter.ai/api/v1/models")
            response.raise_for_status()
            models_data = response.json().get("data", [])

            self._free_model_ids = {
                m['id'] for m in models_data
                if m.get('id', '').endswith(':free')
            }
            self._last_fetch_time = time.time()
            logger.info(f"Successfully refreshed free models cache. Found {len(self._free_model_ids)} free models.")
        except httpx.HTTPError as e:
            logger.error(f"Failed to refresh free models cache: {e}")
            # In case of failure, we keep the old cache but log an error.
            # We'll try again on the next request after the TTL.
            self._last_fetch_time = time.time() # Still update time to prevent spamming failed requests

    async def is_model_allowed(self, model_id: str) -> bool:
        """
        Checks if a given model ID is in the cached list of free models.
        Refreshes the cache if it's stale.
        """
        async with self._lock:
            is_cache_stale = (time.time() - self._last_fetch_time) > self._cache_ttl
            if not self._free_model_ids or is_cache_stale:
                await self._refresh_cache()

        return model_id in self._free_model_ids
