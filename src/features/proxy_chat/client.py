# src/features/proxy_chat/client.py
import httpx
from typing import AsyncGenerator, Dict, Any

from fastapi import HTTPException

from src.shared.config import config, logger
from src.shared.constants import RATE_LIMIT_ERROR_CODE
from src.shared.utils import mask_key
from src.services.key_manager import KeyManager

class OpenRouterClient:
    """Handles the logic of sending requests to OpenRouter with retries."""

    def __init__(self, http_client: httpx.AsyncClient, key_manager: KeyManager):
        self._client = http_client
        self._key_manager = key_manager

    async def send_non_stream(
        self, request_data: Dict[str, Any], max_retries: int = 10
    ) -> Dict[str, Any]:
        """Sends a non-streaming request with retries."""
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                api_key = await self._key_manager.get_next_key()
            except Exception:
                raise HTTPException(status_code=503, detail="All API keys are currently unavailable.")

            logger.info(
                "Attempt %d/%d (non-stream): Using key %s for model '%s'.",
                attempt + 1, max_retries, mask_key(api_key), request_data.get("model")
            )
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            try:
                response = await self._client.post(
                    f"{config['openrouter']['base_url']}/chat/completions",
                    json=request_data,
                    headers=headers,
                )
                response.raise_for_status()
                logger.info("Attempt %d succeeded with key %s.", attempt + 1, mask_key(api_key))
                return response.json()
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == RATE_LIMIT_ERROR_CODE:
                    logger.warning(
                        "Key %s rate limited. Disabling and retrying...", mask_key(api_key)
                    )
                    await self._key_manager.disable_key(api_key)
                    continue
                else:
                    logger.error("HTTP error from OpenRouter: %s - %s", e.response.status_code, e.response.text)
                    raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
            except httpx.RequestError as e:
                last_error = e
                logger.error("Request error occurred: %s", e)
                raise HTTPException(status_code=500, detail=f"Request to OpenRouter API failed: {e}")

        logger.error("All %d retry attempts failed. Last error: %s", max_retries, last_error)
        if isinstance(last_error, httpx.HTTPStatusError):
            raise HTTPException(status_code=last_error.response.status_code, detail=last_error.response.text)

        raise HTTPException(status_code=503, detail="All retry attempts failed.")

    async def send_stream(
        self, request_data: Dict[str, Any], max_retries: int = 10
    ) -> AsyncGenerator[bytes, None]:
        """Sends a streaming request with retries as an async generator."""
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                api_key = await self._key_manager.get_next_key()
            except Exception:
                logger.error("All keys are in cooldown. Cannot process stream.")
                return

            logger.info(
                "Attempt %d/%d (stream): Using key %s for model '%s'.",
                attempt + 1, max_retries, mask_key(api_key), request_data.get("model")
            )
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            try:
                async with self._client.stream(
                    "POST",
                    f"{config['openrouter']['base_url']}/chat/completions",
                    json=request_data,
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    logger.info("Stream started successfully with key %s.", mask_key(api_key))
                    async for chunk in response.aiter_bytes():
                        yield chunk
                    return
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == RATE_LIMIT_ERROR_CODE:
                    logger.warning(
                        "Key %s rate limited on stream. Disabling and retrying...", mask_key(api_key)
                    )
                    await self._key_manager.disable_key(api_key)
                    continue
                else:
                    logger.error("HTTP error during stream: %s", e)
                    break
            except httpx.RequestError as e:
                last_error = e
                logger.error("Request error during stream: %s", e)
                break

        logger.error("All %d stream retry attempts failed. Last error: %s", max_retries, last_error)
