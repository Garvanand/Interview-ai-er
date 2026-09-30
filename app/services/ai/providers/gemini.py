import os
import time
import logging
from typing import Any, TypeVar, Type, Dict
from pydantic import BaseModel
from google import genai
from google.genai import types

from .base import AIProvider

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class GeminiProvider(AIProvider):
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

    def generate_structured(self, prompt: str, schema: Type[T], max_retries: int = 3, timeout_seconds: int = 30) -> T:
        for attempt in range(max_retries):
            try:
                # The official way to enforce structured output in google-genai
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                    )
                )
                
                # Parse output via schema (which allows robust JSON parsing)
                raw_json = response.text
                if not raw_json:
                    raise ValueError("Empty response received from Gemini")
                
                # We can just validate JSON into the Pydantic schema
                return schema.model_validate_json(raw_json)
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Gemini generation failed after {max_retries} attempts. Last error: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "provider": "google-gemini",
            "model_name": self.model_name,
        }
