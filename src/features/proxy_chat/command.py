from pydantic import BaseModel
from typing import Optional

class ProxyChatRequest(BaseModel):
    # Add fields relevant to your chat completion request
    # For example, 'messages', 'model', 'max_tokens', 'temperature', etc.
    # You'll need to align this with the actual OpenRouter API request body.
    # This is a placeholder, adapt it to your needs.
    stream: Optional[bool] = False
    completion: dict  # Placeholder for the full request body

class ProxyChatResponse(BaseModel):
    completion: dict
