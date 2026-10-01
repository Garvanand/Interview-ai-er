"""
Compatibility re-export from canonical app.ai package.
"""
from app.ai import (
    AssessmentEngine,
    AIProvider,
    GeminiProvider,
    GroqProvider,
    get_ai_provider,
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
