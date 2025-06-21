from pydantic import BaseModel
from typing import List, Dict, Any

class ListModelsResponse(BaseModel):
    """
    Response model for the list models endpoint, mirroring the API structure.
    """
    data: List[Dict[str, Any]]
