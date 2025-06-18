from fastapi import Depends
import httpx
from src.shared.config import config, logger
from .command import ProxyChatRequest, ProxyChatResponse
from src.dependencies import get_http_client, get_key_manager


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
        response.raise_for_status()
        return ProxyChatResponse(completion=response.json())
