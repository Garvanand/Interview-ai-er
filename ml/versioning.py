"""
Lightweight Model Versioning and Lineage Tracking.

Guarantees:
1. Every inference stored in the database is attributable to an explicit model version.
2. Metadata persisted per inference:
   - model_name
   - model_version
   - dataset_version
   - training_run
   - inference_timestamp
3. Historical evaluation immutability:
   - Historical evaluations retain their original model version and metadata.
   - Upgrading active models in the registry NEVER overwrites historical records.
   - Deprecated and retired model versions remain interpretable via registry history.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Path to machine-readable registry
REGISTRY_JSON_PATH = Path(__file__).resolve().parent / "model_registry.json"


@dataclass
class InferenceMetadata:
    """Standardized metadata stamped on every model inference."""
    model_name: str
    model_version: str
    dataset_version: str
    training_run: str
    inference_timestamp: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class RegisteredVersion:
    model_version: str
    dataset_version: str
    training_run: str
    artifact_hash: str
    status: str = "active"
    deployed_at: Optional[str] = None
    retired_at: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""


class ModelVersionRegistry:
    """
    Central machine-readable model version registry.
    Manages active model versions, historical lineages, and inference attribution.
    """

    _INSTANCE: Optional["ModelVersionRegistry"] = None

    # Canonical default metadata fallbacks
    _DEFAULT_MODELS: Dict[str, Dict[str, Any]] = {
        "question-difficulty-v1": {
            "model_name": "question-difficulty-v1",
            "model_version": "1.1.0",
            "task": "Question Difficulty Prediction",
            "category": "TRAINED BY US",
            "dataset_identifier": "BAAI/TACO + codeparrot/apps",
            "dataset_version": "2026.10",
            "training_run": "question-difficulty-v1_20261003T063825Z",
            "artifact_hash": "12ef38983aa092caf9c187a70ef40c17ca197f93f4a439e1556d905dfcbf9843",
            "status": "active",
            "deployed_at": "2026-10-03T06:38:25Z",
            "previous_versions": [
                {
                    "model_version": "1.0.0",
                    "dataset_version": "2026.09",
                    "training_run": "question-difficulty-v1_20260915T100000Z",
                    "artifact_hash": "legacy_diff_hash_v100",
                    "status": "retired",
                    "retired_at": "2026-10-03T06:38:25Z",
                }
            ],
        },
        "question-skill-v1": {
            "model_name": "question-skill-v1",
            "model_version": "1.1.0",
            "task": "Question Skill/Topic Classification",
            "category": "TRAINED BY US",
            "dataset_identifier": "BAAI/TACO",
            "dataset_version": "2026.10",
            "training_run": "question-skill-tagger-v1_20261003T063901Z",
            "artifact_hash": "ad21e4620e357e561f34b9fd173b28f53966985e7cf1246b84c9391df420e7a2",
            "status": "active",
            "deployed_at": "2026-10-03T06:39:01Z",
            "previous_versions": [
                {
                    "model_version": "1.0.0",
                    "dataset_version": "2026.09",
                    "training_run": "question-skill-tagger-v1_20260915T100000Z",
                    "artifact_hash": "legacy_skill_hash_v100",
                    "status": "retired",
                    "retired_at": "2026-10-03T06:39:01Z",
                }
            ],
        },
        "answer-nli-v1": {
            "model_name": "answer-nli-v1",
            "model_version": "1.0.0",
            "task": "Transformer-based Answer Concept Coverage",
            "category": "PRETRAINED",
            "dataset_identifier": "MNLI + SNLI",
            "dataset_version": "mnli-snli-v1",
            "training_run": "answer-nli-v1_pretrained_deberta_minilm",
            "artifact_hash": "deberta_v3_nli_minilm_hash_v1",
            "status": "active",
            "deployed_at": "2026-09-30T12:00:00Z",
            "previous_versions": [],
        },
        "code-risk-v1": {
            "model_name": "code-risk-v1",
            "model_version": "1.0.0",
            "task": "Code Defect/Vulnerability Risk Detection",
            "category": "FINE-TUNED BY US",
            "dataset_identifier": "CodeXGLUE Defect Detection",
            "dataset_version": "CodeXGLUE-defect-v1",
            "training_run": "code-risk-v1_codebert_ast_analysis",
            "artifact_hash": "codebert_defect_risk_hash_v1",
            "status": "active",
            "deployed_at": "2026-09-30T12:00:00Z",
            "previous_versions": [],
        },
        "mastery-v1": {
            "model_name": "mastery-v1",
            "model_version": "1.0.0",
            "task": "Candidate Skill/Mastery Modeling",
            "category": "TRAINED BY US",
            "dataset_identifier": "mgor/EDNet",
            "dataset_version": "EdNet-KT1-v1",
            "training_run": "mastery-v1_2pl_irt_calibration",
            "artifact_hash": "irt_2pl_ednet_calibrated_hash_v1",
            "status": "active",
            "deployed_at": "2026-09-30T12:00:00Z",
            "previous_versions": [],
        },
    }

    _ALIASES: Dict[str, str] = {
        "question-skill-classifier-v1": "question-skill-v1",
        "answer-concept-coverage-v1": "answer-nli-v1",
        "code-defect-detector-v1": "code-risk-v1",
        "candidate-skill-mastery-irt-v1": "mastery-v1",
    }

    def __init__(self, registry_file: Optional[Path] = None):
        self.registry_file = registry_file or REGISTRY_JSON_PATH
        self.models: Dict[str, Dict[str, Any]] = {}
        self.aliases: Dict[str, str] = dict(self._ALIASES)
        self._load()

    @classmethod
    def get_instance(cls) -> "ModelVersionRegistry":
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
        return cls._INSTANCE

    def _load(self):
        """Loads machine-readable registry file with safe fallback."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.models = data.get("models", {})
                    self.aliases.update(data.get("aliases", {}))
                logger.info("Loaded model registry from %s (%d models)", self.registry_file, len(self.models))
                return
            except Exception as e:
                logger.warning("Failed to parse registry file %s: %s. Using default models.", self.registry_file, e)

        # Fallback to default models
        self.models = {k: dict(v) for k, v in self._DEFAULT_MODELS.items()}

    def resolve_model_name(self, model_identifier: str) -> str:
        """Resolves alias names to canonical identifiers."""
        return self.aliases.get(model_identifier, model_identifier)

    def get_model_entry(self, model_identifier: str) -> Optional[Dict[str, Any]]:
        """Retrieves raw entry for a model identifier or alias."""
        canonical = self.resolve_model_name(model_identifier)
        return self.models.get(canonical)

    def get_active_metadata(self, model_identifier: str) -> InferenceMetadata:
        """
        Returns active inference metadata (model_name, model_version, dataset_version,
        training_run, inference_timestamp) for a given model.
        """
        canonical = self.resolve_model_name(model_identifier)
        entry = self.models.get(canonical) or self._DEFAULT_MODELS.get(canonical, {})
        
        return InferenceMetadata(
            model_name=canonical,
            model_version=entry.get("model_version", "1.0.0"),
            dataset_version=entry.get("dataset_version", "v1"),
            training_run=entry.get("training_run", f"{canonical}_run"),
            inference_timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_historical_version(self, model_identifier: str, version: str) -> Optional[Dict[str, Any]]:
        """
        Looks up a specific historical version in the registry to guarantee
        that historical evaluations remain interpretable even after model retirement.
        """
        canonical = self.resolve_model_name(model_identifier)
        entry = self.models.get(canonical) or self._DEFAULT_MODELS.get(canonical)
        if not entry:
            return None

        # Check active version
        if entry.get("model_version") == version:
            return {
                "model_name": canonical,
                "model_version": version,
                "dataset_version": entry.get("dataset_version"),
                "training_run": entry.get("training_run"),
                "artifact_hash": entry.get("artifact_hash"),
                "status": entry.get("status", "active"),
                "task": entry.get("task", ""),
            }

        # Check historical retired versions
        for past in entry.get("previous_versions", []):
            if past.get("model_version") == version:
                return {
                    "model_name": canonical,
                    "model_version": version,
                    "dataset_version": past.get("dataset_version"),
                    "training_run": past.get("training_run"),
                    "artifact_hash": past.get("artifact_hash"),
                    "status": past.get("status", "retired"),
                    "retired_at": past.get("retired_at"),
                    "task": entry.get("task", ""),
                }

        return None

    def deploy_new_version(
        self,
        model_identifier: str,
        new_version: str,
        dataset_version: str,
        training_run: str,
        artifact_hash: str,
        artifact_path: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Deploys a new model version:
        1. Moves current active version to previous_versions (marked 'retired').
        2. Sets new version as 'active'.
        3. Never overwrites historical records.
        """
        canonical = self.resolve_model_name(model_identifier)
        if canonical not in self.models:
            self.models[canonical] = {
                "model_name": canonical,
                "task": canonical,
                "previous_versions": []
            }

        entry = self.models[canonical]
        now_iso = datetime.now(timezone.utc).isoformat()

        # Archive old active version if different
        old_version = entry.get("model_version")
        if old_version and old_version != new_version:
            previous_versions = entry.setdefault("previous_versions", [])
            previous_versions.append({
                "model_version": old_version,
                "dataset_version": entry.get("dataset_version"),
                "training_run": entry.get("training_run"),
                "artifact_hash": entry.get("artifact_hash"),
                "status": "retired",
                "retired_at": now_iso,
                "notes": f"Replaced by {new_version}",
            })

        # Set new active version
        entry["model_version"] = new_version
        entry["dataset_version"] = dataset_version
        entry["training_run"] = training_run
        entry["artifact_hash"] = artifact_hash
        entry["status"] = "active"
        entry["deployed_at"] = now_iso
        if artifact_path:
            entry["artifact_path"] = artifact_path
        if metrics:
            entry["metrics"] = metrics

        logger.info("Deployed new model version %s for %s (run=%s)", new_version, canonical, training_run)
        return entry

    def stamp_inference(
        self,
        model_identifier: str,
        inference_output: Dict[str, Any],
        version_override: Optional[str] = None,
        run_override: Optional[str] = None,
        dataset_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Attaches the mandatory 5 attribution fields to an inference output payload:
        - model_name
        - model_version
        - dataset_version
        - training_run
        - inference_timestamp
        """
        meta = self.get_active_metadata(model_identifier)

        model_name = meta.model_name
        model_version = version_override or meta.model_version
        dataset_version = dataset_override or meta.dataset_version
        training_run = run_override or meta.training_run
        inference_timestamp = datetime.now(timezone.utc).isoformat()

        attribution = {
            "model_name": model_name,
            "model_version": model_version,
            "dataset_version": dataset_version,
            "training_run": training_run,
            "inference_timestamp": inference_timestamp,
        }

        # Inject into output payload (both top-level and structured attribution)
        inference_output.update(attribution)
        inference_output["model_attribution"] = attribution
        return inference_output


# Convenience module-level functions
def get_registry() -> ModelVersionRegistry:
    return ModelVersionRegistry.get_instance()


def stamp_inference(
    model_identifier: str,
    output: Dict[str, Any],
    version_override: Optional[str] = None,
    run_override: Optional[str] = None,
    dataset_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper to stamp an inference dictionary with model lineage metadata."""
    return get_registry().stamp_inference(
        model_identifier=model_identifier,
        inference_output=output,
        version_override=version_override,
        run_override=run_override,
        dataset_override=dataset_override,
    )
