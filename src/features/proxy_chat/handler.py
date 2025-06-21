from fastapi import Depends
import httpx
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

        # Check if the response is successful
        if response.status_code != 200:
            logger.error(f"Error from OpenRouter API: {response.status_code} - {response.text}")
            response.raise_for_status()

        # Check if the response content is not empty
        if not response.content:
            logger.error("Empty response from OpenRouter API")
            raise ValueError("Empty response from OpenRouter API")

        try:
            return ProxyChatResponse(completion=response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise
        except ValueError as e:
            logger.error(f"JSON decoding error: {e}")
            raise
