import httpx
from typing import Optional
from src.shared.config import config, logger
from src.services.key_manager import KeyManager
from .command import ProxyChatRequest, ProxyChatResponse

class ProxyChatHandler:
    def __init__(
        self, 
        http_client: httpx.AsyncClient,
        key_manager: KeyManager
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
        response.raise_for_status()
        return ProxyChatResponse(completion=response.json())
