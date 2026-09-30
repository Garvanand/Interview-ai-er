import os
import pytest
from unittest.mock import MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "https://dummy.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "dummy-key")
os.environ.setdefault("GEMINI_API_KEY", "dummy-gemini-key")

from app import create_app


@pytest.fixture(scope="module")
def app():
    application = create_app()
    application.config["TESTING"] = True
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


def _auth_mock(mock_client, user_id="user-123"):
    mock_client.return_value.auth.get_user.return_value.user.id = user_id
    mock_client.return_value.auth.get_user.return_value.user.email = f"{user_id}@example.com"


def test_get_longitudinal_analytics_endpoint(client):
    """
    The /api/analytics/<user_id> endpoint must return the full structured analytics payload.
    Supabase is mocked so this test does not require a real database connection.
    """
    mock_sessions = [
        {
            "id": "sess-1",
            "user_id": "user-123",
            "interview_type": "Fullstack",
            "start_time": "2026-09-01T10:00:00Z",
            "score": 75.0,
            "status": "completed",
        }
    ]
    mock_questions = [
        {
            "id": "q-1",
            "session_id": "sess-1",
            "question_text": "Design a rate limiter",
            "interview_type": "Fullstack",
            "difficulty": "intermediate",
            "skill_focus": "System Design",
            "evaluation_score": 75.0,
            "evaluation_details": {
                "strengths": ["Clear architecture"],
                "weaknesses": ["No Redis cache specified"],
            },
            "created_at": "2026-09-01T10:05:00Z",
        }
    ]

    with patch("app.api.analytics.analytics_service.supabase") as mock_supabase, \
         patch("app.auth.supabase_service._get_client") as mock_auth_client:

        _auth_mock(mock_auth_client)
        mock_supabase.get_user_sessions.return_value = mock_sessions
        mock_supabase.get_user_skill_profiles.return_value = []
        mock_supabase.get_recommendations.return_value = []
        mock_db = MagicMock()
        mock_db.table().select().in_().order().execute().data = mock_questions
        mock_supabase._get_client.return_value = mock_db

        response = client.get(
            "/api/analytics/user-123",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    payload = data["data"]
    assert payload["user_id"] == "user-123"
    assert "score_trends" in payload
    assert "skill_trends" in payload
    assert "difficulty_progression" in payload
    assert "consistency" in payload
    assert "repeated_weaknesses" in payload
    assert "next_practice_recommendations" in payload
    assert payload["score_trends"]["total_sessions_analyzed"] == 1


def test_filter_options_endpoint(client):
    """
    The /api/analytics/filter-options/<user_id> endpoint must return
    available filter choices derived from the user's real stored records.
    """
    mock_sessions = [
        {"id": "s1", "interview_type": "Frontend", "start_time": "2026-09-01T00:00:00Z"}
    ]
    mock_questions = [
        {
            "id": "q1",
            "skill_focus": "React/CSS",
            "difficulty": "beginner",
            "created_at": "2026-09-01T00:00:00Z",
        }
    ]

    with patch("app.api.analytics.analytics_service.supabase") as mock_supabase, \
         patch("app.auth.supabase_service._get_client") as mock_auth_client:

        _auth_mock(mock_auth_client)
        mock_supabase.get_user_sessions.return_value = mock_sessions
        mock_supabase.get_user_skill_profiles.return_value = [{"skill_name": "React/CSS"}]
        mock_supabase.get_recommendations.return_value = []
        mock_db = MagicMock()
        mock_db.table().select().in_().order().execute().data = mock_questions
        mock_supabase._get_client.return_value = mock_db

        response = client.get(
            "/api/analytics/filter-options/user-123",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    opts = data["data"]
    assert "Frontend" in opts["interview_types"]
    assert "React/CSS" in opts["skills"]
    assert "beginner" in opts["difficulties"]
