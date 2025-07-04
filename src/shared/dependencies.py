#!/usr/bin/env python3
"""
Dependency provider functions for the application.
"""

from fastapi import Request
import httpx

from src.services.key_manager import KeyManager
from src.services.model_filter_service import ModelFilterService
from src.features.proxy_chat.client import OpenRouterClient

def get_http_client(request: Request) -> httpx.AsyncClient:
    """Returns the shared httpx.AsyncClient instance."""
    return request.app.state.http_client

def get_key_manager(request: Request) -> KeyManager:
    """Returns the shared KeyManager instance."""
    return request.app.state.key_manager

def get_model_filter_service(request: Request) -> ModelFilterService:
    """Returns the shared ModelFilterService instance."""
    return request.app.state.model_filter_service

def get_openrouter_client(request: Request) -> OpenRouterClient:
    """Returns the shared OpenRouterClient instance."""
    return request.app.state.openrouter_client
