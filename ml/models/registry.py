"""
Model Registry management and metadata tracking.
Enforces semantic versioning, execution categories, and hardware constraints.
"""
from __future__ import annotations

import enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


class ModelCategory(str, enum.Enum):
    TRAINED_BY_US = "TRAINED BY US"
    FINE_TUNED_BY_US = "FINE-TUNED BY US"
    PRETRAINED = "PRETRAINED"
    DETERMINISTIC = "DETERMINISTIC"
    LLM_GENERATED = "LLM-GENERATED"


class HardwareTarget(str, enum.Enum):
    CPU = "CPU"
    GPU = "GPU"
    ANY = "CPU or GPU"


@dataclass
class ModelMetadata:
    model_id: str
    capability: str
    category: ModelCategory
    base_model: str
    version: str
    hardware_target: HardwareTarget
    expected_latency_ms: int
    is_optional: bool
    weights_path: Optional[str] = None
    description: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


class MLModelRegistry:
    """Central catalog of all models in the Interview AI platform."""

    _MODELS: Dict[str, ModelMetadata] = {
        "question-difficulty-v1": ModelMetadata(
            model_id="question-difficulty-v1",
            capability="Question Difficulty Prediction",
            category=ModelCategory.TRAINED_BY_US,
            base_model="all-MiniLM-L6-v2 + Ridge/MLP Classifier",
            version="1.0.0",
            hardware_target=HardwareTarget.CPU,
            expected_latency_ms=25,
            is_optional=False,
            description="Predicts beginner, intermediate, or advanced difficulty from question text."
        ),
        "question-skill-classifier-v1": ModelMetadata(
            model_id="question-skill-classifier-v1",
            capability="Question Skill/Topic Classification",
            category=ModelCategory.TRAINED_BY_US,
            base_model="all-MiniLM-L6-v2 + MultiOutput Logistic Regression",
            version="1.0.0",
            hardware_target=HardwareTarget.CPU,
            expected_latency_ms=20,
            is_optional=False,
            description="Multi-label classification of technical topics and taxonomy skills."
        ),
        "answer-concept-coverage-v1": ModelMetadata(
            model_id="answer-concept-coverage-v1",
            capability="Transformer-based Answer Concept Coverage",
            category=ModelCategory.PRETRAINED,
            base_model="cross-encoder/nli-deberta-v3-base",
            version="1.0.0",
            hardware_target=HardwareTarget.ANY,
            expected_latency_ms=150,
            is_optional=False,
            description="Natural Language Inference cross-encoder to compute conceptual rubric coverage."
        ),
        "semantic-answer-similarity-v1": ModelMetadata(
            model_id="semantic-answer-similarity-v1",
            capability="Semantic Answer Similarity",
            category=ModelCategory.PRETRAINED,
            base_model="sentence-transformers/all-MiniLM-L6-v2",
            version="1.0.0",
            hardware_target=HardwareTarget.CPU,
            expected_latency_ms=15,
            is_optional=False,
            description="Dense sentence embeddings with cosine similarity for semantic drift and recall."
        ),
        "code-defect-detector-v1": ModelMetadata(
            model_id="code-defect-detector-v1",
            capability="Code Defect/Vulnerability Risk Detection",
            category=ModelCategory.FINE_TUNED_BY_US,
            base_model="microsoft/codebert-base",
            version="1.0.0",
            hardware_target=HardwareTarget.ANY,
            expected_latency_ms=180,
            is_optional=True,
            description="Sequence classification model detecting potential defects, vulnerabilities, and boundary flaws."
        ),
        "voice-stt-whisper-v1": ModelMetadata(
            model_id="voice-stt-whisper-v1",
            capability="Speech-to-Text for voice interviews",
            category=ModelCategory.PRETRAINED,
            base_model="openai/whisper-base.en",
            version="1.0.0",
            hardware_target=HardwareTarget.ANY,
            expected_latency_ms=450,
            is_optional=True,
            description="Local speech-to-text audio transcription for spoken candidate answers."
        ),
        "candidate-skill-mastery-irt-v1": ModelMetadata(
            model_id="candidate-skill-mastery-irt-v1",
            capability="Candidate Skill/Mastery Modeling",
            category=ModelCategory.TRAINED_BY_US,
            base_model="2-Parameter Logistic Item Response Theory (2PL-IRT) / BKT",
            version="1.0.0",
            hardware_target=HardwareTarget.CPU,
            expected_latency_ms=1,
            is_optional=False,
            description="Probabilistic latent ability and skill mastery estimation calibrated via EdNet."
        ),
        "adaptive-question-selector-v1": ModelMetadata(
            model_id="adaptive-question-selector-v1",
            capability="ML-assisted adaptive question selection",
            category=ModelCategory.TRAINED_BY_US,
            base_model="Fisher Information CAT + Thompson Sampling",
            version="1.0.0",
            hardware_target=HardwareTarget.CPU,
            expected_latency_ms=5,
            is_optional=False,
            description="Optimal adaptive next-question recommendation maximizing skill information gain."
        ),
    }

    @classmethod
    def get(cls, model_id: str) -> Optional[ModelMetadata]:
        return cls._MODELS.get(model_id)

    @classmethod
    def list_all(cls) -> List[ModelMetadata]:
        return list(cls._MODELS.values())
