from __future__ import annotations

import logging
import os
import time
from typing import Any

from config.settings import get_env

logger = logging.getLogger(__name__)


class ApiKeyManager:
    def __init__(self) -> None:
        self.key_names = ["GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]
        self.available_keys = [
            key for key in (get_env(name) for name in self.key_names) if key and key.strip()
        ]
        self.failure_counters: dict[str, int] = {}

    def get_configured_keys(self) -> list[str]:
        return self.available_keys.copy()

    def mask_key(self, key: str | None) -> str:
        if not key:
            return "non configurée"
        if len(key) <= 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"

    def get_active_key(self) -> str | None:
        if not self.available_keys:
            return None
        return self.available_keys[0]

    def mark_failure(self, key: str, reason: str) -> None:
        self.failure_counters[key] = self.failure_counters.get(key, 0) + 1
        logger.warning("Gemini key failure for %s: %s", self.mask_key(key), reason)

    def reset_failure(self, key: str) -> None:
        self.failure_counters.pop(key, None)

    def has_usable_key(self) -> bool:
        return bool(self.available_keys)
