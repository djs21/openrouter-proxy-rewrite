from fastapi import APIRouter, Depends
from .query import ListModelsResponse
from .handler import ListModelsHandler

router = APIRouter()

@router.get("/models", response_model=ListModelsResponse, tags=["Proxy"])
async def list_models(
    handler: ListModelsHandler = Depends(ListModelsHandler),
) -> ListModelsResponse:
    """
    Returns a list of available OpenRouter models.
    The list is filtered to free models if 'free_only' is enabled in config.
    """
    return await handler.handle()
