"""
Google Gemini structured AI provider using google.genai.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.ai.providers.base import AIProvider

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GeminiProvider(AIProvider):
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        max_retries: int = 3,
        timeout_seconds: int = 30,
    ) -> T:
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                    ),
                )

                raw_json = response.text
                if not raw_json:
                    raise ValueError("Empty response received from Gemini")

                return schema.model_validate_json(raw_json)

            except Exception as e:
                logger.warning("Attempt %d/%d failed: %s", attempt + 1, max_retries, e)
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Gemini generation failed after {max_retries} attempts: {e}")
                time.sleep(2 ** attempt)

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "provider": "google-gemini",
            "model_name": self.model_name,
        }
