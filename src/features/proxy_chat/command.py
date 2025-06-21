from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ProxyChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    model: str
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stop: Optional[List[str]] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    response_format: Optional[Dict[str, str]] = None
    seed: Optional[int] = None
    stream: Optional[bool] = False

class ProxyChatResponse(BaseModel):
    completion: dict
