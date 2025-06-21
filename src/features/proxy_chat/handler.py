# src/features/proxy_chat/handler.py
from fastapi import Depends, HTTPException
import httpx
from fastapi.responses import StreamingResponse

from src.shared.config import config
from src.shared.dependencies import get_http_client, get_key_manager, get_model_filter_service
from src.services.key_manager import KeyManager
from src.services.model_filter_service import ModelFilterService

from .command import ProxyChatRequest, ProxyChatResponse
from .client import OpenRouterClient

class ProxyChatHandler:
    def __init__(
        self,
        http_client: httpx.AsyncClient = Depends(get_http_client),
        key_manager: KeyManager = Depends(get_key_manager),
        model_filter: ModelFilterService = Depends(get_model_filter_service),
    ):
        self._model_filter = model_filter
        self._client = OpenRouterClient(http_client, key_manager)

    async def handle(self, request: ProxyChatRequest):
        if config["openrouter"].get("free_only", False):
            if not await self._model_filter.is_model_allowed(request.model):
                raise HTTPException(
                    status_code=403,
                    detail=f"Proxy is configured for free models only. '{request.model}' is not a valid free model."
                )

        is_streaming = request.stream if hasattr(request, "stream") else False
        request_data = request.dict(exclude_unset=True)

        if is_streaming:
            stream_generator = self._client.send_stream(request_data)
            return StreamingResponse(
                stream_generator,
                media_type="text/event-stream",
            )

        completion = await self._client.send_non_stream(request_data)
        return ProxyChatResponse(completion=completion)
