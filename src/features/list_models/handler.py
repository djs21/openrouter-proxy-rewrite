from typing import Dict, Any, List
from fastapi import Depends
from config import config
from .query import ListModelsResponse
from src.services.model_filter_service import ModelFilterService
from src.dependencies import get_model_filter_service

class ListModelsHandler:
    """
    Handles the business logic for listing models.
    It uses the ModelFilterService to get model data and applies filtering
    based on the application's configuration.
    """
    def __init__(
        self,
        model_filter: ModelFilterService = Depends(get_model_filter_service),
    ):
        self._model_filter = model_filter

    async def handle(self) -> ListModelsResponse:
        """
        Fetches all models and filters them if the 'free_only' config is set.
        """
        all_models = await self._model_filter.get_models()

        if not config["openrouter"].get("free_only", False):
            return ListModelsResponse(data=all_models)

        free_model_ids = await self._model_filter.get_free_model_ids()
        filtered_data = [
            model for model in all_models if model.get("id") in free_model_ids
        ]

        return ListModelsResponse(data=filtered_data)
