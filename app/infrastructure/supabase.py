"""
Supabase client infrastructure.

Lazy-initialized singleton client tied to Flask application configuration.
"""
from __future__ import annotations

import logging
from typing import Optional
from flask import current_app
from supabase import Client, create_client

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Lazy-initialized, singleton Supabase client for a Flask request context."""
    _client: Optional[Client] = None

    @classmethod
    def get(cls) -> Client:
        if cls._client is None:
            url = current_app.config.get("SUPABASE_URL")
            key = current_app.config.get("SUPABASE_KEY")
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured")
            cls._client = create_client(url, key)
            logger.info("SupabaseClient initialized successfully")
        return cls._client

    @classmethod
    def reset(cls) -> None:
        """Force client re-initialization (useful in testing)."""
        cls._client = None
