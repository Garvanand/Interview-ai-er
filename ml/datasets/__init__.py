"""
Dataset ingestion and normalization interfaces for technical assessment benchmarks.
"""
from __future__ import annotations

from .taco_loader import TACODatasetLoader
from .apps_loader import APPSDatasetLoader
from .codexglue_loader import CodeXGLUEDefectLoader
from .ednet_loader import EdNetDatasetLoader

__all__ = [
    "TACODatasetLoader",
    "APPSDatasetLoader",
    "CodeXGLUEDefectLoader",
    "EdNetDatasetLoader",
]
