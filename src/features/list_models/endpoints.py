from fastapi import APIRouter, Depends
from .query import ListModelsResponse
from .handler import ListModelsHandler

router = APIRouter()

@router.get("/models", response_model=ListModelsResponse)
async def list_models(
    handler: ListModelsHandler = Depends()
):
    return await handler.handle()
