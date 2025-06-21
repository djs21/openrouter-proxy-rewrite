#!/usr/bin/env python3
"""
Dependency provider functions for the application.
"""

from fastapi import Request
import httpx

from src.services.key_manager import KeyManager
from src.features.model_filter.service import ModelFilterService

def get_http_client(request: Request) -> httpx.AsyncClient:
    """Returns the shared httpx.AsyncClient instance."""
    return request.app.state.http_client

def get_key_manager(request: Request) -> KeyManager:
    """Returns the shared KeyManager instance."""
    return request.app.state.key_manager

def get_model_filter_service(request: Request) -> ModelFilterService:
    """Returns the shared ModelFilterService instance."""
    return request.app.state.model_filter_service
