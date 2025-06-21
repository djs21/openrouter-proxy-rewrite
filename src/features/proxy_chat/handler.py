from fastapi import Depends, HTTPException
import httpx
import json
from config import config, logger
from fastapi.responses import StreamingResponse
from .command import ProxyChatRequest, ProxyChatResponse
from src.dependencies import get_http_client, get_key_manager
from src.services.key_manager import KeyManager
from utils import mask_key
from constants import RATE_LIMIT_ERROR_CODE

class ProxyChatHandler:
    def __init__(
        self,
        http_client: httpx.AsyncClient = Depends(get_http_client),
        key_manager: KeyManager = Depends(get_key_manager)
    ):
        self._client = http_client
        self._key_manager = key_manager

    async def _streamer(self, request: ProxyChatRequest, headers: dict):
        """Helper generator for streaming logic, used inside the retry loop."""
        async with self._client.stream(
            "POST",
            f"{config['openrouter']['base_url']}/chat/completions",
            json=request.dict(exclude_unset=True),
            headers=headers,
        ) as response:
            # raise_for_status() will throw an exception for 4xx/5xx responses,
            # which is caught by the main handler logic to trigger a retry.
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk

    async def handle(self, request: ProxyChatRequest):
        # A generous number of retries. In a high-traffic scenario, this could
        # be the total number of available keys.
        max_retries = 10
        last_error = None

        for attempt in range(max_retries):
            try:
                api_key = await self._key_manager.get_next_key()
            except Exception:
                logger.error("Failed to get a key from KeyManager. All keys might be in cooldown.")
                raise HTTPException(status_code=503, detail="All API keys are currently unavailable.")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            try:
                is_streaming = request.stream if hasattr(request, "stream") else False

                if is_streaming:
                    return StreamingResponse(
                        self._streamer(request, headers),
                        media_type="text/event-stream",
                    )

                # Non-streaming logic
                response = await self._client.post(
                    f"{config['openrouter']['base_url']}/chat/completions",
                    json=request.dict(exclude_unset=True),
                    headers=headers,
                )
                response.raise_for_status()

                # Success! Return the response and exit the loop.
                return ProxyChatResponse(completion=response.json())

            except httpx.HTTPStatusError as e:
                last_error = e
                # Check if the error is a rate limit error
                if e.response.status_code == RATE_LIMIT_ERROR_CODE:
                    logger.warning(
                        f"Key {mask_key(api_key)} rate limited (attempt {attempt + 1}/{max_retries}). Disabling and retrying..."
                    )
                    # This is the crucial step: disable the key that was rate-limited
                    await self._key_manager.disable_key(api_key)
                    continue  # Continue to the next attempt in the loop
                else:
                    # For any other HTTP error, fail immediately
                    logger.error(f"HTTP error from OpenRouter: {e.response.status_code} - {e.response.text}")
                    raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

            except httpx.RequestError as e:
                # For network errors, also fail immediately
                logger.error(f"Request error occurred: {e}")
                raise HTTPException(status_code=500, detail=f"Request to OpenRouter API failed: {e}")

        # If the loop finishes, all retry attempts have failed.
        logger.error(f"All {max_retries} retry attempts failed. The last error was: {last_error}")
        if isinstance(last_error, httpx.HTTPStatusError):
            raise HTTPException(status_code=last_error.response.status_code, detail=last_error.response.text)
        else:
            raise HTTPException(status_code=503, detail="All retry attempts failed to get a successful response.")
