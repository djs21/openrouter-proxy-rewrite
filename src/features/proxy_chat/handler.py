from fastapi import Depends, HTTPException
import httpx
import json
from config import config, logger
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

    async def handle(self, request: ProxyChatRequest) -> ProxyChatResponse:
        api_key = await self._key_manager.get_next_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        response = await self._client.post(
            f"{config['openrouter']['base_url']}/chat/completions",
            json=request.dict(),
            headers=headers
        )

        try:
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            return ProxyChatResponse(completion=response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred from OpenRouter: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise HTTPException(status_code=500, detail=f"Request to OpenRouter API failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error from OpenRouter API: {e}. Response content: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to parse response from OpenRouter API")
