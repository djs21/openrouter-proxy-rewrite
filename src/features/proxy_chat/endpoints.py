from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from .command import ProxyChatRequest
from .handler import ProxyChatHandler

router = APIRouter()

@router.post("/chat/completions", response_model=None)
async def proxy_chat(
    request: Request,
    chat_request: ProxyChatRequest,
    handler: ProxyChatHandler = Depends(ProxyChatHandler)
) -> StreamingResponse | dict:
    return await handler.handle(chat_request)
