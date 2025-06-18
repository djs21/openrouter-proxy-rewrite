from fastapi import APIRouter, Depends
from .handler import HealthCheckHandler
from .query import HealthCheckResponse

router = APIRouter()

@router.get("/health", response_model=HealthCheckResponse, tags=["Monitoring"])
async def health_check(handler = Depends()) -> HealthCheckResponse:
    return await handler.handle()
