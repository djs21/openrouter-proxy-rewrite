from .command import DisableKeyRequest, DisableKeyResponse
from src.services.key_manager import KeyManager

class DisableKeyHandler:
    def __init__(self, key_manager: KeyManager):
        self._key_manager = key_manager

    async def handle(self, command: DisableKeyRequest) -> DisableKeyResponse:
        await self._key_manager.disable_key(
            key=command.key,
            reset_time_ms=command.reset_time_ms
        )
        return DisableKeyResponse(status="ok")
