from abc import ABC, abstractmethod
from typing import Any, TypeVar, Type, Optional, Dict
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class AIProvider(ABC):
    @abstractmethod
    def generate_structured(self, prompt: str, schema: Type[T], max_retries: int = 3, timeout_seconds: int = 30) -> T:
        """
        Generate structured output adhering to the provided Pydantic schema.
        
        Args:
            prompt: The full prompt instructions.
            schema: The Pydantic model class to validate against.
            max_retries: Number of retries on failure.
            timeout_seconds: Request timeout in seconds.
            
        Returns:
            An instance of the schema class.
            
        Raises:
            Exception: If generation fails after retries.
        """
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        Return metadata about the current provider (e.g. model name, version).
        """
        pass
