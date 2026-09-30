"""
Authorization tests for the Interview AI backend.

These tests verify:
1. All protected endpoints return 401 when no Authorization header is provided.
2. All protected endpoints return 401 when a malformed token is provided.
3. Cross-user access to session resources returns 403.
4. Accessing your own session proceeds (200/201).
5. User-scoped path parameters (user_id) return 403 when mismatched.
6. Error codes are machine-readable and consistent.

Design:
- Each test mocks app.auth.supabase_service._get_client to inject a controlled identity.
- Tests do NOT hit real Supabase endpoints.
- All environment variables are stubbed before app import.
"""
import pytest
import os
from unittest.mock import patch, MagicMock

# Stub environment variables before any app import
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-anon-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

from app import create_app
from flask import json


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    application = create_app()
    application.config["TESTING"] = True
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


def _mock_auth_success(mock_get_client, user_id="test-user-abc"):
    """Configure the auth mock to return a successful user verification."""
    mock_supabase = MagicMock()
    mock_supabase.auth.get_user.return_value.user.id = user_id
    mock_supabase.auth.get_user.return_value.user.email = f"{user_id}@example.com"
    mock_get_client.return_value = mock_supabase
    return mock_supabase


# ─────────────────────────────────────────────────────────────────
# 1. Missing Authorization header → 401
# ─────────────────────────────────────────────────────────────────

PROTECTED_ENDPOINTS = [
    ("POST", "/api/start_session", {"interview_type": "Software Engineer"}),
    ("GET", "/api/get_question", None),
    ("POST", "/api/submit_answer", {"session_id": "s", "question_id": "q", "answer_text": "answer"}),
    ("GET", "/api/session/some-session-id", None),
    ("GET", "/api/session/some-session-id/state", None),
    ("POST", "/api/end_session/some-session-id", {}),
    ("GET", "/api/user/some-user-id/sessions", None),
    ("POST", "/api/follow_up_question", {"question": "q", "answer": "a", "interview_type": "t"}),
    ("GET", "/api/intelligence/skills/some-user-id", None),
    ("GET", "/api/analytics/some-user-id", None),
]

@patch("app.auth.supabase_service._get_client")
@pytest.mark.parametrize("method,path,body", PROTECTED_ENDPOINTS)
def test_missing_auth_header_returns_401(mock_get_client, method, path, body, client):
    """Every protected endpoint must return 401 when Authorization header is absent."""
    if method == "POST":
        response = client.post(path, json=body or {})
    else:
        response = client.get(path)

    assert response.status_code == 401, (
        f"{method} {path} returned {response.status_code}, expected 401"
    )
    data = json.loads(response.data)
    assert data.get("success") is False or data.get("error") is True
    assert data.get("code") in ("AUTHENTICATION_REQUIRED", "EMPTY_TOKEN", "INVALID_TOKEN", "AUTHENTICATION_FAILED")


# ─────────────────────────────────────────────────────────────────
# 2. Malformed token → 401
# ─────────────────────────────────────────────────────────────────

@patch("app.auth.supabase_service._get_client")
def test_malformed_token_format_returns_401(mock_get_client, client):
    """Non-Bearer token scheme must be rejected immediately."""
    response = client.post(
        "/api/start_session",
        json={"interview_type": "Software Engineer"},
        headers={"Authorization": "Basic dXNlcjpwYXNz"},  # Basic auth, not Bearer
    )
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data["code"] == "AUTHENTICATION_REQUIRED"


@patch("app.auth.supabase_service._get_client")
def test_empty_bearer_token_returns_401(mock_get_client, client):
    """'Bearer ' with no token must be rejected."""
    response = client.post(
        "/api/start_session",
        json={"interview_type": "Software Engineer"},
        headers={"Authorization": "Bearer "},
    )
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data["code"] in ("EMPTY_TOKEN", "INVALID_TOKEN", "AUTHENTICATION_FAILED")


@patch("app.auth.supabase_service._get_client")
def test_invalid_token_content_returns_401(mock_get_client, client):
    """A syntactically valid but unverifiable token must return 401."""
    mock_get_client.return_value.auth.get_user.return_value.user = None
    response = client.post(
        "/api/start_session",
        json={"interview_type": "Software Engineer"},
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────
# 3. Cross-user session access → 403
# ─────────────────────────────────────────────────────────────────

@patch("app.auth.supabase_service.get_session")
@patch("app.auth.supabase_service._get_client")
def test_cross_user_session_access_returns_403(mock_get_client, mock_get_session, client):
    """User A must not be able to read User B's session."""
    _mock_auth_success(mock_get_client, user_id="user-A")
    mock_get_session.return_value = {"id": "session-B", "user_id": "user-B", "status": "active"}

    response = client.get(
        "/api/session/session-B",
        headers={"Authorization": "Bearer token-for-user-A"},
    )

    assert response.status_code == 403
    data = json.loads(response.data)
    assert data.get("error") is True
    assert data.get("code") == "UNAUTHORIZED"


@patch("app.auth.supabase_service.get_session")
@patch("app.auth.supabase_service._get_client")
def test_cross_user_session_state_access_returns_403(mock_get_client, mock_get_session, client):
    """User A must not be able to access User B's orchestrator state."""
    _mock_auth_success(mock_get_client, user_id="user-A")
    mock_get_session.return_value = {"id": "session-B", "user_id": "user-B"}

    response = client.get(
        "/api/session/session-B/state",
        headers={"Authorization": "Bearer token-for-user-A"},
    )

    assert response.status_code == 403


@patch("app.auth.supabase_service.get_session")
@patch("app.auth.supabase_service._get_client")
def test_cross_user_end_session_returns_403(mock_get_client, mock_get_session, client):
    """User A must not be able to end User B's session."""
    _mock_auth_success(mock_get_client, user_id="user-A")
    mock_get_session.return_value = {"id": "session-B", "user_id": "user-B"}

    response = client.post(
        "/api/end_session/session-B",
        json={},
        headers={"Authorization": "Bearer token-for-user-A"},
    )

    assert response.status_code == 403


# ─────────────────────────────────────────────────────────────────
# 4. Own-session access proceeds
# ─────────────────────────────────────────────────────────────────

@patch("app.api.interview.supabase_service.get_session_statistics")
@patch("app.auth.supabase_service.get_session")
@patch("app.auth.supabase_service._get_client")
def test_own_session_access_proceeds(mock_get_client, mock_auth_get_session, mock_get_stats, client):
    """User A must be able to read their own session."""
    _mock_auth_success(mock_get_client, user_id="user-A")
    mock_auth_get_session.return_value = {"id": "session-A", "user_id": "user-A", "status": "active"}
    mock_get_stats.return_value = {"session_id": "session-A", "score": 75.0}

    response = client.get(
        "/api/session/session-A",
        headers={"Authorization": "Bearer valid-token-for-user-A"},
    )

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────
# 5. Path user_id mismatch → 403
# ─────────────────────────────────────────────────────────────────

@patch("app.auth.supabase_service._get_client")
def test_user_id_path_mismatch_on_sessions_returns_403(mock_get_client, client):
    """Accessing /user/<other_user_id>/sessions must return 403."""
    _mock_auth_success(mock_get_client, user_id="user-A")

    response = client.get(
        "/api/user/user-B/sessions",
        headers={"Authorization": "Bearer valid-token-for-user-A"},
    )

    assert response.status_code == 403


@patch("app.auth.supabase_service._get_client")
def test_intelligence_skills_path_mismatch_returns_403(mock_get_client, client):
    """Accessing /intelligence/skills/<other_user_id> must return 403."""
    _mock_auth_success(mock_get_client, user_id="user-A")

    response = client.get(
        "/api/intelligence/skills/user-B",
        headers={"Authorization": "Bearer valid-token-for-user-A"},
    )

    assert response.status_code == 403


@patch("app.auth.supabase_service._get_client")
def test_analytics_path_mismatch_returns_403(mock_get_client, client):
    """Accessing /analytics/<other_user_id> must return 403."""
    _mock_auth_success(mock_get_client, user_id="user-A")

    response = client.get(
        "/api/analytics/user-B",
        headers={"Authorization": "Bearer valid-token-for-user-A"},
    )

    assert response.status_code == 403


# ─────────────────────────────────────────────────────────────────
# 6. Error response shape is consistent
# ─────────────────────────────────────────────────────────────────

@patch("app.auth.supabase_service._get_client")
def test_401_response_shape(mock_get_client, client):
    """401 responses must include success=False, error=True, message, and code."""
    response = client.get("/api/session/some-session")
    data = json.loads(response.data)

    assert response.status_code == 401
    assert "message" in data
    assert "code" in data
    # Either error=True or success=False must be present
    assert data.get("error") is True or data.get("success") is False


@patch("app.auth.supabase_service.get_session")
@patch("app.auth.supabase_service._get_client")
def test_403_response_shape(mock_get_client, mock_get_session, client):
    """403 responses must include error=True, message, and code='UNAUTHORIZED'."""
    _mock_auth_success(mock_get_client, user_id="user-A")
    mock_get_session.return_value = {"id": "session-B", "user_id": "user-B"}

    response = client.get(
        "/api/session/session-B",
        headers={"Authorization": "Bearer token-for-user-A"},
    )
    data = json.loads(response.data)

    assert response.status_code == 403
    assert data.get("error") is True
    assert data.get("code") == "UNAUTHORIZED"
    assert "message" in data
