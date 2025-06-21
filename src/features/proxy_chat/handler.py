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

    async def _stream_with_retries(self, request: ProxyChatRequest):
        """
        A dedicated generator that handles the entire streaming and retry logic.
        This ensures exceptions are caught within the generator's own lifecycle.
        """
        max_retries = 10
        last_error = None

        for attempt in range(max_retries):
            try:
                api_key = await self._key_manager.get_next_key()
            except Exception:
                logger.error("Failed to get a key from KeyManager. All keys might be in cooldown.")
                # In a generator, we can't raise HTTPException. We just stop.
                return

            logger.info(f"Attempt {attempt + 1}/{max_retries} (stream): Using key {mask_key(api_key)} for model '{request.model}'.")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            try:
                async with self._client.stream(
                    "POST",
                    f"{config['openrouter']['base_url']}/chat/completions",
                    json=request.dict(exclude_unset=True),
                    headers=headers,
                ) as response:
                    response.raise_for_status()

                    logger.info(f"Attempt {attempt + 1} (stream) succeeded. Streaming with key {mask_key(api_key)}.")

                    # Success! Stream the response body and then exit the loop.
                    async for chunk in response.aiter_bytes():
                        yield chunk
                    return

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == RATE_LIMIT_ERROR_CODE:
                    logger.warning(
                        f"Key {mask_key(api_key)} rate limited on stream attempt {attempt + 1}/{max_retries}. Disabling and retrying..."
                    )
                    await self._key_manager.disable_key(api_key)
                    continue  # Go to the next attempt
                else:
                    logger.error(f"HTTP error during stream with key {mask_key(api_key)}: {e.response.status_code}")
                    break # For other errors, stop trying

            except httpx.RequestError as e:
                last_error = e
                logger.error(f"Request error during stream with key {mask_key(api_key)}: {e}")
                break # Stop trying on network errors

        # If the loop completes, all retries failed. The client will receive an empty response.
        logger.error(f"All {max_retries} stream retry attempts failed. Last error: {last_error}")

    async def handle(self, request: ProxyChatRequest):
        is_streaming = request.stream if hasattr(request, "stream") else False

        if is_streaming:
            # For streaming, we call our new dedicated generator
            return StreamingResponse(
                self._stream_with_retries(request),
                media_type="text/event-stream",
            )

        # --- Non-streaming logic remains the same and works correctly ---
        max_retries = 10
        last_error = None

        for attempt in range(max_retries):
            try:
                api_key = await self._key_manager.get_next_key()
            except Exception:
                logger.error("Failed to get a key from KeyManager. All keys might be in cooldown.")
                raise HTTPException(status_code=503, detail="All API keys are currently unavailable.")

            logger.info(f"Attempt {attempt + 1}/{max_retries} (non-stream): Using key {mask_key(api_key)} for model '{request.model}'.")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            try:
                response = await self._client.post(
                    f"{config['openrouter']['base_url']}/chat/completions",
                    json=request.dict(exclude_unset=True),
                    headers=headers,
                )
                response.raise_for_status()

                logger.info(f"Attempt {attempt + 1} succeeded with key {mask_key(api_key)}.")
                return ProxyChatResponse(completion=response.json())

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == RATE_LIMIT_ERROR_CODE:
                    logger.warning(
                        f"Key {mask_key(api_key)} rate limited (attempt {attempt + 1}/{max_retries}). Disabling and retrying..."
                    )
                    await self._key_manager.disable_key(api_key)
                    continue
                else:
                    logger.error(f"HTTP error from OpenRouter: {e.response.status_code} - {e.response.text}")
                    raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

            except httpx.RequestError as e:
                last_error = e
                logger.error(f"Request error occurred: {e}")
                raise HTTPException(status_code=500, detail=f"Request to OpenRouter API failed: {e}")

        logger.error(f"All {max_retries} retry attempts failed. The last error was: {last_error}")
        if isinstance(last_error, httpx.HTTPStatusError):
            raise HTTPException(status_code=last_error.response.status_code, detail=last_error.response.text)
        else:
            raise HTTPException(status_code=503, detail="All retry attempts failed to get a successful response.")
