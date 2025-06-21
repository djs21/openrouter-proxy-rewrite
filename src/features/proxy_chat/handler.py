from fastapi import Depends, HTTPException
import httpx
import json
from config import config, logger
from fastapi.responses import StreamingResponse
from .command import ProxyChatRequest, ProxyChatResponse
from src.dependencies import get_http_client, get_key_manager
from src.services.key_manager import KeyManager

class ProxyChatHandler:
    def __init__(
        self,
        http_client: httpx.AsyncClient = Depends(get_http_client),
        key_manager: KeyManager = Depends(get_key_manager)
    ):
        self._client = http_client
        self._key_manager = key_manager

    async def handle(self, request: ProxyChatRequest):
        api_key = await self._key_manager.get_next_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        is_streaming = request.stream if hasattr(request, 'stream') else False

        response = await self._client.post(
            f"{config['openrouter']['base_url']}/chat/completions",
            json=request.dict(exclude_unset=True),
            headers=headers,
            stream=is_streaming  # Enable streaming for httpx if the client requests it
        )

        try:
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses

            if is_streaming:
                async def generate_stream():
                    async for chunk in response.aiter_bytes():
                        yield chunk
                return StreamingResponse(generate_stream(), media_type="text/event-stream")
            else:
                # For non-streaming requests, assume a single JSON response
                try:
                    return ProxyChatResponse(completion=response.json())
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decoding error for non-streaming response from OpenRouter API: {e}. Response content: {response.text}")
                    raise HTTPException(status_code=500, detail="Failed to parse non-streaming response from OpenRouter API")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred from OpenRouter: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise HTTPException(status_code=500, detail=f"Request to OpenRouter API failed: {e}")
