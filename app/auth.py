"""
app/auth.py — Compatibility shim re-exporting from app.security.

Preferred import: `from app.security import require_auth, verify_session_ownership, ...`
"""
from app.security.auth import (
    require_auth,
    verify_session_ownership,
    verify_user_ownership,
    unauthorized_response,
    not_found_response,
    _supabase_service as supabase_service,
)

__all__ = [
    "require_auth",
    "verify_session_ownership",
    "verify_user_ownership",
    "unauthorized_response",
    "not_found_response",
    "supabase_service",
]
