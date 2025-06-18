from pydantic import BaseModel
from typing import List, Dict, Any

class ListModelsResponse(BaseModel):
    data: List[Dict[str, Any]]
