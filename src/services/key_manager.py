"""
KeyManager service for OpenRouter API Proxy.
Manages API key rotation and rate limit handling.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import HTTPException

from src.shared.config import config, logger
from src.shared.utils import mask_key
from src.shared.metrics import ACTIVE_KEYS, COOLDOWN_KEYS

class KeyManager:
    """Manages OpenRouter API keys, including rotation and rate limit handling."""
    def __init__(self, keys: List[str], cooldown_seconds: int, strategy: str, opts: list[str]):
        self.keys = keys
        self.cooldown_seconds = cooldown_seconds
        self.current_index = 0
        self.disabled_until: Dict[str, datetime] = {}
        self.strategy = strategy
        self.use_last_key = "same" in opts
        self.last_key = None
        self.lock = asyncio.Lock()
        self.update_metrics()

    def update_metrics(self):
        """Update Prometheus metrics for keys"""
        now_ = datetime.now()
        active_keys = [k for k in self.keys if k not in self.disabled_until or self.disabled_until[k] <= now_]
        cooldown_keys = [k for k in self.keys if k in self.disabled_until and self.disabled_until[k] > now_]
        ACTIVE_KEYS.set(len(active_keys))
        COOLDOWN_KEYS.set(len(cooldown_keys))

    async def get_next_key(self) -> str:
        """Get the next available API key using round-robin selection."""
        async with self.lock:
            now_ = datetime.now()
            available_keys = set()
            expired_keys = []
            for key in self.keys:
                if key in self.disabled_until:
                    if now_ >= self.disabled_until[key]:
                        expired_keys.append(key)
                    else:
                        continue
                available_keys.add(key)
                
            for key in expired_keys:
                if key in self.disabled_until:
                    del self.disabled_until[key]
                    logger.info("API key %s is now enabled again.", mask_key(key))

            if not available_keys:
                soonest_available = min(self.disabled_until.values())
                wait_seconds = (soonest_available - now_).total_seconds()
                logger.error(
                    "All API keys are currently disabled. The next key will be available in %.2f seconds.", 
                    wait_seconds,
                )
                raise HTTPException(
                    status_code=503,
                    detail="All API keys are currently disabled due to rate limits. Please try again later."
                )

            if self.use_last_key and self.last_key in available_keys:
                selected_key = self.last_key
            elif self.strategy == "round-robin":
                for _ in range(len(self.keys)):
                    key = self.keys[self.current_index]
                    self.current_index = (self.current_index + 1) % len(self.keys)
                    if key in available_keys:
                        selected_key = key
                        break
            elif self.strategy == "first":
                selected_key = next(iter(available_keys))
            elif self.strategy == "random":
                selected_key = random.choice(list(available_keys))
            else:
                raise RuntimeError(f"Unknown key selection strategy: {self.strategy}")
            self.last_key = selected_key
            self.update_metrics()
            return selected_key

    async def disable_key(self, key: str, reset_time_ms: Optional[int] = None):
        """
        Disable a key until reset time or for the configured cooldown period.

        Args:
            key: The API key to disable
            reset_time_ms: Optional reset time in milliseconds since epoch. If provided,
                           the key will be disabled until this time. Otherwise, the default
                           cooldown period will be used.
        """
        async with self.lock:
            now_ = datetime.now()
            if reset_time_ms:
                try:
                    reset_datetime = datetime.fromtimestamp(reset_time_ms / 1000)
                    if reset_datetime > now_:
                        disabled_until = reset_datetime
                        logger.info("Using server-provided reset time: %s", str(disabled_until))
                    else:
                        disabled_until = now_ + timedelta(seconds=self.cooldown_seconds)
                        logger.warning(
                            "Server-provided reset time is in the past, using default cooldown of %s seconds", self.cooldown_seconds)
                except Exception as e:
                    disabled_until = now_ + timedelta(seconds=self.cooldown_seconds)
                    logger.error(
                        "Error processing reset time %s, using default cooldown: %s", reset_time_ms, e)
            else:
                disabled_until = now_ + timedelta(seconds=self.cooldown_seconds)
                logger.info(
                    "No reset time provided, using default cooldown of %s seconds", self.cooldown_seconds)

            self.disabled_until[key] = disabled_until
            self.update_metrics()
            logger.warning(
                "API key %s has been disabled until %s.", mask_key(key), disabled_until)
