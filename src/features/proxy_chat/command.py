from pydantic import BaseModel
from typing import Optional, Dict, Any

class ProxyChatRequest(BaseModel):
    model: str
    messages: list[Dict[str, Any]]
    stream: bool = False
    # ... other chat completion fields ...

class ProxyChatResponse(BaseModel):
    completion: Dict[str, Any]
