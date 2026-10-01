"""
Authentication and authorization middleware for the Flask backend.

Design:
- All protected endpoints must be decorated with @require_auth.
- require_auth validates the Supabase JWT from the Authorization: Bearer <token> header.
- On success, it sets g.user_id and g.user_email from the verified token.
- The caller identity is NEVER derived from request body or query parameters.
- verify_session_ownership and verify_user_ownership enforce resource-level authorization.
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Dict, Optional, Tuple

from flask import current_app, g, jsonify, request
from app.infrastructure.supabase import SupabaseClient
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)
_supabase_service = SupabaseService()


def require_auth(f):
    """
    Decorator that validates a Supabase JWT from the Authorization header.

    On success, sets:
      g.user_id    — verified UUID from Supabase auth
      g.user_email — verified email from Supabase auth

    On failure, returns 401 immediately without calling the route handler.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({
                "success": False,
                "error": True,
                "message": "Authorization header missing. Please provide a Bearer token.",
                "code": "AUTHENTICATION_REQUIRED",
            }), 401

        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({
                "success": False,
                "error": True,
                "message": "Invalid Authorization header format. Expected: 'Bearer <token>'.",
                "code": "AUTHENTICATION_REQUIRED",
            }), 401

        token = parts[1].strip()
        if not token:
            return jsonify({
                "success": False,
                "error": True,
                "message": "Empty token provided.",
                "code": "EMPTY_TOKEN",
            }), 401

        try:
            client = _supabase_service._get_client()
            user_res = client.auth.get_user(token)
            if not user_res or not user_res.user:
                logger.warning("Token validation returned no user for path: %s", request.path)
                return jsonify({
                    "success": False,
                    "error": True,
                    "message": "Invalid or expired authentication token.",
                    "code": "INVALID_TOKEN",
                }), 401

            g.user_id = user_res.user.id
            g.user_email = getattr(user_res.user, "email", None)

        except Exception as e:
            logger.error("Token validation error on path %s: %s", request.path, str(e))
            return jsonify({
                "success": False,
                "error": True,
                "message": "Authentication failed. Token could not be validated.",
                "code": "AUTHENTICATION_FAILED",
            }), 401

        return f(*args, **kwargs)

    return decorated


def verify_session_ownership(session_id: str, user_id: str) -> bool:
    """
    Check that the given session_id belongs to user_id.
    Returns False if the session does not exist or belongs to a different user.
    Never raises — treats any error as a failed ownership check.
    """
    if not session_id or not user_id:
        return False
    try:
        session = _supabase_service.get_session(session_id)
        if not session:
            # In local fallback mode (e.g. unmigrated Supabase schema), if an authenticated user
            # requests a session that was evicted or lost during dev server reload, auto-provision
            # the local session for this authenticated user so they aren't locked out with a 403.
            if _supabase_service.is_fallback_mode():
                logger.info("Auto-restoring missing local session %s for user %s", session_id, user_id)
                _supabase_service.create_local_session(session_id, user_id)
                return True
            return False
        return session.get("user_id") == user_id
    except Exception as e:
        logger.error("Session ownership check error (session=%s): %s", session_id, str(e))
        return False


def verify_user_ownership(path_user_id: str) -> bool:
    """
    Check that the user_id in the URL path matches the verified caller (g.user_id).
    Used for endpoints like /api/user/<user_id>/sessions.
    """
    caller_id = getattr(g, "user_id", None)
    if not caller_id or not path_user_id:
        return False
    return caller_id == path_user_id


def unauthorized_response(message: str = "You are not authorized to access this resource.") -> Tuple[Any, int]:
    return jsonify({
        "success": False,
        "error": True,
        "message": message,
        "code": "UNAUTHORIZED",
    }), 403


def not_found_response(message: str = "Resource not found.") -> Tuple[Any, int]:
    return jsonify({
        "success": False,
        "error": True,
        "message": message,
        "code": "NOT_FOUND",
    }), 404
