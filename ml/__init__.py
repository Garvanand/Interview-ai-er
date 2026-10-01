"""
Machine Learning Layer for Interview Intelligence Platform.

This package provides offline training, dataset curation, and low-latency
local inference modules for:
1. Question Difficulty Prediction (TACO/APPS + Classical Head)
2. Question Skill/Topic Classification (MiniLM + MultiOutput Head)
3. Transformer Answer Concept Coverage (DeBERTa-v3 NLI)
4. Semantic Answer Similarity (all-MiniLM-L6-v2)
5. Code Defect & Vulnerability Risk Detection (CodeBERT + CodeXGLUE)
6. Speech-to-Text Transcription (Whisper-base.en)
7. Candidate Skill Mastery Modeling (2PL-IRT / BKT from EdNet)
8. ML-Assisted Adaptive Question Selection (Fisher Information CAT)
"""
from __future__ import annotations

__version__ = "0.1.0"
