from fastapi import APIRouter, Depends, Request
from .query import ListModelsResponse
from .handler import ListModelsHandler

router = APIRouter()

def make_handler(request: Request) -> ListModelsHandler:
    http_client = request.app.state.http_client
    return ListModelsHandler(http_client)

@router.get("/models", response_model=ListModelsResponse)
async def list_models(
    handler: ListModelsHandler = Depends(make_handler)
) -> ListModelsResponse:
    return await handler.handle()
