"""
Intelligence Classes and Fallback Framework for ML Components.

Three Classes of Intelligence:
1. PRIMARY ML ("ml"): Trained/fine-tuned local models.
2. SECONDARY MODEL ("pretrained" or "deterministic"): Pretrained transformer or static/heuristic analysis.
3. LLM FALLBACK ("llm"): Structured Gemini reasoning.

Every result must explicitly indicate its `source`:
- "ml"
- "pretrained"
- "llm"
- "deterministic"
- "unavailable"

Confidence must reflect the actual method and never be manufactured.
"""
from __future__ import annotations

import enum
import logging
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class IntelligenceSource(str, enum.Enum):
    ML = "ml"
    PRETRAINED = "pretrained"
    LLM = "llm"
    DETERMINISTIC = "deterministic"
    UNAVAILABLE = "unavailable"


def log_fallback_event(
    component: str,
    from_source: str,
    to_source: str,
    reason: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Structured logging for observability whenever an ML component falls back."""
    payload = {
        "event": "ml_fallback_triggered",
        "component": component,
        "from_source": from_source,
        "to_source": to_source,
        "reason": str(reason),
        "timestamp": time.time(),
    }
    if extra:
        payload["extra"] = extra
    logger.warning("ML Fallback: %s", payload)


# ─────────────────────────────────────────────────────────────────────────────
# Structured Pydantic Schemas for Gemini LLM Fallbacks
# ─────────────────────────────────────────────────────────────────────────────

class DifficultyLLMSchema(BaseModel):
    difficulty: str = Field(description="One of 'beginner', 'intermediate', or 'advanced'")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0 reflecting certainty")
    reasoning: str = Field(description="Short rationale for the difficulty assignment")


class ConceptItemLLMSchema(BaseModel):
    concept: str = Field(description="The technical concept evaluated")
    status: str = Field(description="'covered', 'partially_covered', 'missing', or 'contradicted'")
    score: float = Field(description="Score between 0.0 and 1.0")
    explanation: str = Field(description="Brief explanation of how the answer covered or missed it")


class ConceptCoverageLLMSchema(BaseModel):
    overall_coverage_pct: float = Field(description="Overall coverage percentage from 0.0 to 100.0")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    concept_results: List[ConceptItemLLMSchema] = Field(description="Evaluation for each concept")


class CodeDefectLLMSchema(BaseModel):
    defect_probability: float = Field(description="Estimated probability of defect or bug between 0.0 and 1.0")
    risk_band: str = Field(description="'low', 'medium', or 'high'")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    risk_indicators: List[str] = Field(description="List of detected defect or vulnerability risks")
    analysis: str = Field(description="Summary of the code quality analysis")


# ─────────────────────────────────────────────────────────────────────────────
# LLM Fallback Invocation Functions
# ─────────────────────────────────────────────────────────────────────────────

def try_llm_difficulty_fallback(question_text: str) -> Optional[Dict[str, Any]]:
    """Attempts structured LLM reasoning via Gemini for question difficulty."""
    try:
        from app.ai.providers import get_ai_provider
        provider = get_ai_provider()
    except Exception as e:
        logger.debug("LLM provider unavailable for difficulty fallback: %s", e)
        return None

    prompt = (
        "You are an expert technical interviewer. Classify the technical difficulty of the following "
        "interview question into exactly one of: 'beginner', 'intermediate', or 'advanced'.\n\n"
        f"Question:\n{question_text}\n\n"
        "Return structured JSON matching the schema with realistic confidence (never artificially 1.0)."
    )

    try:
        parsed, telemetry = provider.generate_structured(prompt, DifficultyLLMSchema)
        diff = parsed.difficulty.lower().strip()
        if diff not in ("beginner", "intermediate", "advanced"):
            diff = "intermediate"
        conf = max(0.0, min(1.0, float(parsed.confidence)))
        return {
            "difficulty": diff,
            "predicted_difficulty": diff,
            "confidence": conf,
            "source": IntelligenceSource.LLM.value,
            "method": "gemini_structured_reasoning",
            "reasoning": parsed.reasoning,
            "probabilities": {
                diff: conf,
                **{c: round((1.0 - conf) / 2.0, 4) for c in ("beginner", "intermediate", "advanced") if c != diff}
            },
            "model_version": "gemini_fallback_v1",
        }
    except Exception as e:
        logger.warning("Gemini difficulty fallback failed: %s", e)
        return None


def try_llm_concept_coverage_fallback(
    candidate_answer: str,
    expected_concepts: List[str],
) -> Optional[Dict[str, Any]]:
    """Attempts structured LLM reasoning via Gemini for concept coverage."""
    if not expected_concepts:
        return None

    try:
        from app.ai.providers import get_ai_provider
        provider = get_ai_provider()
    except Exception as e:
        logger.debug("LLM provider unavailable for concept coverage fallback: %s", e)
        return None

    concepts_bulleted = "\n".join(f"- {c}" for c in expected_concepts)
    prompt = (
        "Evaluate whether the candidate's answer covers the required technical concepts.\n\n"
        f"Required Concepts:\n{concepts_bulleted}\n\n"
        f"Candidate Answer:\n{candidate_answer}\n\n"
        "For each concept, determine if it is 'covered', 'partially_covered', 'missing', or 'contradicted'. "
        "Calculate an overall coverage percentage (0-100) and provide realistic confidence."
    )

    try:
        parsed, telemetry = provider.generate_structured(prompt, ConceptCoverageLLMSchema)
        concept_results = []
        covered, missing, partial, contradicted = [], [], [], []

        for item in parsed.concept_results:
            st = item.status.lower().strip()
            if st not in ("covered", "partially_covered", "missing", "contradicted"):
                st = "partially_covered" if item.score >= 0.4 else "missing"

            score = max(0.0, min(1.0, float(item.score)))
            entailment = score if st in ("covered", "partially_covered") else 0.1
            contradiction = 0.8 if st == "contradicted" else 0.05
            neutral = max(0.0, 1.0 - entailment - contradiction)

            res_entry = {
                "concept": item.concept,
                "entailment_probability": round(entailment, 4),
                "contradiction_probability": round(contradiction, 4),
                "neutral_probability": round(neutral, 4),
                "semantic_similarity": round(score, 4),
                "concept_score": round(score, 4),
                "status": st,
                "explanation": item.explanation,
            }
            concept_results.append(res_entry)

            if st == "covered":
                covered.append(item.concept)
            elif st == "missing":
                missing.append(item.concept)
            elif st == "partially_covered":
                partial.append(item.concept)
            elif st == "contradicted":
                contradicted.append(item.concept)

        overall_pct = max(0.0, min(100.0, float(parsed.overall_coverage_pct)))
        conf = max(0.0, min(1.0, float(parsed.confidence)))

        return {
            "overall_coverage_pct": round(overall_pct, 1),
            "concept_results": concept_results,
            "covered_concepts": covered,
            "missing_concepts": missing,
            "contradicted_concepts": contradicted,
            "partially_covered_concepts": partial,
            "source": IntelligenceSource.LLM.value,
            "method": "gemini_concept_analysis",
            "confidence": conf,
            "signal_type": "llm_derived_concept_coverage_signal",
            "aggregation_formula": "LLM structured semantic reasoning",
        }
    except Exception as e:
        logger.warning("Gemini concept coverage fallback failed: %s", e)
        return None


def try_llm_code_defect_fallback(
    code: str,
    language: str = "python",
) -> Optional[Dict[str, Any]]:
    """Attempts structured LLM reasoning via Gemini for code defect & vulnerability risk."""
    try:
        from app.ai.providers import get_ai_provider
        provider = get_ai_provider()
    except Exception as e:
        logger.debug("LLM provider unavailable for code defect fallback: %s", e)
        return None

    prompt = (
        f"Review the following {language} code for potential software defects, boundary condition bugs, "
        "memory/resource leaks, and vulnerability risks.\n\n"
        f"```{language}\n{code}\n```\n\n"
        "Provide an estimated defect probability (0.0 to 1.0), risk band ('low', 'medium', 'high'), "
        "realistic confidence, and a list of specific risk indicators."
    )

    try:
        parsed, telemetry = provider.generate_structured(prompt, CodeDefectLLMSchema)
        defect_prob = max(0.0, min(1.0, float(parsed.defect_probability)))
        band = parsed.risk_band.lower().strip()
        if band not in ("low", "medium", "high"):
            band = "medium" if defect_prob >= 0.3 else "low"
        conf = max(0.0, min(1.0, float(parsed.confidence)))

        return {
            "defect_probability": round(defect_prob, 4),
            "risk_band": band,
            "confidence": conf,
            "source": IntelligenceSource.LLM.value,
            "method": "gemini_code_review",
            "model_version": "gemini_code_review_v1",
            "risk_indicators": parsed.risk_indicators,
            "analysis": parsed.analysis,
            "signal_disclaimer": "This is an LLM-derived code review signal (fallback), not proof of incorrectness.",
        }
    except Exception as e:
        logger.warning("Gemini code defect fallback failed: %s", e)
        return None
