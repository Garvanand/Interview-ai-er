"""
Data storage and local caching utilities for ML training and evaluation artifacts.
"""
from __future__ import annotations

import os
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent
RAW_DATA_DIR = DATA_ROOT / "raw"
PROCESSED_DATA_DIR = DATA_ROOT / "processed"
CACHE_DIR = DATA_ROOT / "cache"

for d in (RAW_DATA_DIR, PROCESSED_DATA_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)
