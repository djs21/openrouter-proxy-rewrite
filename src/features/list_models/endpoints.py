from fastapi import APIRouter, Depends, Request
from .query import ListModelsResponse
from .handler import ListModelsHandler
from httpx import AsyncClient

router = APIRouter()

@router.get("/models", response_model=ListModelsResponse)
async def list_models(
    request: Request,
    handler: ListModelsHandler = Depends(ListModelsHandler)
):
    return await handler.handle()
