# src/features/proxy_chat/handler.py
from fastapi import Depends, HTTPException
import httpx
from fastapi.responses import StreamingResponse, JSONResponse

from src.shared.config import config
from src.shared.dependencies import get_model_filter_service, get_openrouter_client
from src.services.model_filter_service import ModelFilterService

from .command import ProxyChatRequest, ProxyChatResponse
from .client import OpenRouterClient

class ProxyChatHandler:
    def __init__(
        self,
        model_filter: ModelFilterService = Depends(get_model_filter_service),
        openrouter_client: OpenRouterClient = Depends(get_openrouter_client)
    ):
        self._model_filter = model_filter
        self._client = openrouter_client

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
        return JSONResponse(content=completion)
