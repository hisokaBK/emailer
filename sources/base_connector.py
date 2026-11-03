from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    name: str = "base"

    @abstractmethod
    def fetch_jobs(self, query: str = "") -> list[dict[str, Any]]:
        raise NotImplementedError
