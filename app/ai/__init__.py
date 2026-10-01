"""
AI package — structured LLM assessment, structured schemas, and providers.
"""
from app.ai.engine import AssessmentEngine
from app.ai.providers import AIProvider, GeminiProvider, GroqProvider, get_ai_provider
from app.ai.schemas import (
    AnswerEvaluation,
    CodeEvaluation,
    Question,
    SessionSynthesis,
    SkillExtraction,
)

__all__ = [
    "AssessmentEngine",
    "AIProvider",
    "GeminiProvider",
    "GroqProvider",
    "get_ai_provider",
    "AnswerEvaluation",
    "CodeEvaluation",
    "Question",
    "SessionSynthesis",
    "SkillExtraction",
]
