"""
Model Manager for managing singleton model instances and concurrency.
"""
import logging
import threading
from typing import Any, Dict

from .model_registry import MLModelRegistry, ModelMetadata
from .model_loader import ModelLoader

logger = logging.getLogger(__name__)

class ModelManager:
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelManager, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
            
    def _initialize(self):
        self._models: Dict[str, Any] = {}
        # Reentrant concurrency locks per model ID
        self._model_locks: Dict[str, threading.RLock] = {}
        for model_meta in MLModelRegistry.list_all():
            self._model_locks[model_meta.model_id] = threading.RLock()

    def get_model(self, model_id: str) -> Any:
        """Get a loaded model by ID. Loads it lazily if not loaded yet."""
        metadata = MLModelRegistry.get(model_id)
        if not metadata:
            raise ValueError(f"Model {model_id} not found in registry.")
            
        if not metadata.is_enabled:
            raise ValueError(f"Model {model_id} is currently disabled.")

        # If already loaded, return it
        if model_id in self._models:
            return self._models[model_id]

        # Acquire lock to load the model (prevents multiple threads from loading simultaneously)
        lock = self._model_locks.get(model_id)
        if lock is None:
            lock = threading.RLock()
            self._model_locks[model_id] = lock

        with lock:
            # Double check if loaded while waiting for lock
            if model_id in self._models:
                return self._models[model_id]

            logger.info(f"Lazy loading model: {model_id}")
            loaded_model = self._load_model_instance(metadata)
            self._models[model_id] = loaded_model
            
            # Update registry device tracking
            metadata.device = ModelLoader.get_best_device()
            
            return loaded_model

    def _load_model_instance(self, metadata: ModelMetadata) -> Any:
        artifact = metadata.artifact_location
        if not artifact:
            # No physical artifact to load (e.g. IRT or algorithmic baselines)
            return None
            
        if metadata.model_id == "answer-concept-coverage-v1":
            return ModelLoader.load_cross_encoder(metadata.model_id, artifact)
        elif metadata.model_id in ["question-difficulty-v1", "question-skill-classifier-v1", "semantic-answer-similarity-v1"]:
            return ModelLoader.load_sentence_transformer(metadata.model_id, artifact)
        elif metadata.model_id == "code-defect-detector-v1":
            return ModelLoader.load_sequence_classifier(metadata.model_id, artifact)
        elif metadata.model_id == "voice-stt-whisper-v1":
            return ModelLoader.load_whisper(metadata.model_id, artifact)
        
        # Default behavior: assume sentence transformer
        return ModelLoader.load_sentence_transformer(metadata.model_id, artifact)

    def acquire_lock(self, model_id: str) -> threading.RLock:
        """Get the lock for a specific model for controlled concurrency during inference."""
        if model_id not in self._model_locks:
            self._model_locks[model_id] = threading.RLock()
        return self._model_locks[model_id]

    def get_health(self) -> Dict[str, Any]:
        """Returns health information for all models in the registry."""
        health_info = {}
        for metadata in MLModelRegistry.list_all():
            is_loaded = metadata.model_id in self._models
            health_info[metadata.model_id] = {
                "model": metadata.model_id,
                "loaded": is_loaded,
                "device": metadata.device if is_loaded else "unloaded",
                "version": metadata.version,
                "enabled": metadata.is_enabled,
                "task": metadata.task
            }
        return health_info

    def get_model_health(self, model_id: str) -> Dict[str, Any]:
        metadata = MLModelRegistry.get(model_id)
        if not metadata:
            return {"error": "Model not found"}
        is_loaded = model_id in self._models
        return {
            "model": metadata.model_id,
            "loaded": is_loaded,
            "device": metadata.device if is_loaded else "unloaded",
            "version": metadata.version,
            "enabled": metadata.is_enabled,
            "task": metadata.task
        }
