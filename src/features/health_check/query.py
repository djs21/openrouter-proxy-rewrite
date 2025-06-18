from pydantic import BaseModel
from typing import Dict

class HealthCheckResponse(BaseModel):
    status: str
    services: Dict[str, str]
