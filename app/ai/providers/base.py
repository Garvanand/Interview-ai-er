"""
Base AI provider interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIProvider(ABC):
    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        max_retries: int = 3,
        timeout_seconds: int = 30,
    ) -> T:
        """Generate structured output adhering to the provided Pydantic schema."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Return metadata about the current provider (e.g. model name, version)."""
        pass
