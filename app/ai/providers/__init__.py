"""
AI Providers package — supports Groq (openai/gpt-oss-120b) and Google Gemini.
"""
import os
from typing import Optional
from app.ai.providers.base import AIProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.groq import GroqProvider


def get_ai_provider(provider_name: Optional[str] = None) -> AIProvider:
    """Factory to instantiate the active AI provider based on configuration.
    
    Priority:
    1. Explicit provider_name if passed
    2. AI_PROVIDER environment variable ("groq" or "gemini")
    3. GROQ_API_KEY if present -> GroqProvider
    4. GEMINI_API_KEY if present -> GeminiProvider
    """
    choice = (provider_name or os.getenv("AI_PROVIDER", "")).strip().lower()

    if choice == "groq" or (not choice and os.getenv("GROQ_API_KEY")):
        return GroqProvider()
    elif choice == "gemini" or (not choice and os.getenv("GEMINI_API_KEY")):
        return GeminiProvider()
    elif os.getenv("GROQ_API_KEY"):
        return GroqProvider()
    elif os.getenv("GEMINI_API_KEY"):
        return GeminiProvider()

    # Default to GroqProvider which will raise a descriptive error if GROQ_API_KEY is missing
    return GroqProvider()


__all__ = ["AIProvider", "GeminiProvider", "GroqProvider", "get_ai_provider"]
