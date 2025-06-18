from fastapi import APIRouter, Depends, Request
from .command import ProxyChatRequest, ProxyChatResponse
from .handler import ProxyChatHandler
from httpx import AsyncClient
from src.services.key_manager import KeyManager

router = APIRouter()

@router.post("/chat/completions", response_model=ProxyChatResponse)
async def proxy_chat(
    request: Request,
    chat_request: ProxyChatRequest,
    handler: ProxyChatHandler = Depends(ProxyChatHandler)
):
    return await handler.handle(chat_request)
