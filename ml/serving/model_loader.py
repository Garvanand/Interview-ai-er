"""
Model Loader for instantiating machine learning models.
Supports lazy loading, hardware acceleration, and robust error classification
for corrupted artifacts, invalid tokenizers, out-of-memory states, and offline isolation.
"""
import logging
import os
from typing import Any, Optional

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logger = logging.getLogger(__name__)


class ModelLoader:
    @staticmethod
    def get_best_device() -> str:
        """Determines the best available hardware device."""
        if HAS_TORCH and torch.cuda.is_available():
            return "cuda"
        if HAS_TORCH and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    @staticmethod
    def _is_local_only() -> bool:
        """Checks if network downloads are disallowed (default True for zero network dependence)."""
        return os.getenv("ALLOW_NETWORK_DOWNLOAD", "0").lower() not in ("1", "true")

    @staticmethod
    def _handle_loader_exception(model_id: str, artifact_location: str, e: Exception) -> None:
        """Categorize and log loader exceptions cleanly."""
        if HAS_TORCH and hasattr(torch.cuda, "OutOfMemoryError") and isinstance(e, torch.cuda.OutOfMemoryError):
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.error("OOM while loading %s from %s: %s", model_id, artifact_location, e)
        elif isinstance(e, MemoryError):
            logger.error("System MemoryError while loading %s from %s: %s", model_id, artifact_location, e)
        elif isinstance(e, (EOFError, ValueError, OSError, KeyError)):
            logger.warning("Artifact unavailable or invalid for %s at %s: %s", model_id, artifact_location, e)
        else:
            logger.error("Failed to load %s from %s: %s", model_id, artifact_location, e)

    @staticmethod
    def load_sentence_transformer(model_id: str, artifact_location: str, device: str = None) -> Any:
        try:
            from sentence_transformers import SentenceTransformer

            target_device = device or ModelLoader.get_best_device()
            logger.info("Loading SentenceTransformer: %s on %s", artifact_location, target_device)

            local_only = ModelLoader._is_local_only()
            model = SentenceTransformer(artifact_location, device=target_device, local_files_only=local_only)
            return model
        except Exception as e:
            ModelLoader._handle_loader_exception(model_id, artifact_location, e)
            raise

    @staticmethod
    def load_cross_encoder(model_id: str, artifact_location: str, device: str = None) -> Any:
        try:
            from sentence_transformers import CrossEncoder

            target_device = device or ModelLoader.get_best_device()
            logger.info("Loading CrossEncoder: %s on %s", artifact_location, target_device)

            local_only = ModelLoader._is_local_only()
            model = CrossEncoder(artifact_location, device=target_device, local_files_only=local_only)
            return model
        except Exception as e:
            ModelLoader._handle_loader_exception(model_id, artifact_location, e)
            raise

    @staticmethod
    def load_sequence_classifier(model_id: str, artifact_location: str, device: str = None) -> Any:
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            target_device = device or ModelLoader.get_best_device()
            logger.info("Loading SequenceClassifier: %s on %s", artifact_location, target_device)

            local_only = ModelLoader._is_local_only()
            tokenizer = AutoTokenizer.from_pretrained(artifact_location, local_files_only=local_only)
            model = AutoModelForSequenceClassification.from_pretrained(artifact_location, local_files_only=local_only)

            if HAS_TORCH:
                model = model.to(target_device)

            return {"model": model, "tokenizer": tokenizer, "device": target_device}
        except Exception as e:
            ModelLoader._handle_loader_exception(model_id, artifact_location, e)
            raise

    @staticmethod
    def load_whisper(model_id: str, artifact_location: str, device: str = None) -> Any:
        try:
            import whisper

            target_device = device or ModelLoader.get_best_device()
            logger.info("Loading Whisper: %s on %s", artifact_location, target_device)

            name = artifact_location.split("/")[-1]
            model = whisper.load_model(name, device=target_device)
            return model
        except Exception as e:
            ModelLoader._handle_loader_exception(model_id, artifact_location, e)
            raise
