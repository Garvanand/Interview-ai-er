import os
import pytest
from unittest.mock import MagicMock, patch

os.environ.setdefault('SUPABASE_URL', 'https://dummy.supabase.co')
os.environ.setdefault('SUPABASE_KEY', 'dummy-key')
os.environ.setdefault('GEMINI_API_KEY', 'dummy-gemini-key')

from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_get_longitudinal_analytics_endpoint(client):
    """Verifies that the /api/analytics/<user_id> endpoint returns full structured payload."""
    mock_sessions = [
        {
            'id': 'sess-1',
            'user_id': 'user-123',
            'interview_type': 'Fullstack',
            'start_time': '2026-09-01T10:00:00Z',
            'score': 75.0,
            'status': 'completed'
        }
    ]
    mock_questions = [
        {
            'id': 'q-1',
            'session_id': 'sess-1',
            'question_text': 'Design a rate limiter',
            'interview_type': 'Fullstack',
            'difficulty': 'intermediate',
            'skill_focus': 'System Design',
            'evaluation_score': 75.0,
            'evaluation_details': {'strengths': ['Clear architecture'], 'weaknesses': ['No Redis cache specified']},
            'created_at': '2026-09-01T10:05:00Z'
        }
    ]

    with patch('app.routes.analytics.analytics_service.supabase') as mock_supabase, patch('app.auth.supabase_service._get_client') as mock_auth_client:
        mock_auth_client.return_value.auth.get_user.return_value.user.id = 'user-123'
        mock_auth_client.return_value.auth.get_user.return_value.user.email = 'test@example.com'
        mock_supabase.get_user_sessions.return_value = mock_sessions
        mock_supabase.get_user_skill_profiles.return_value = []
        mock_supabase.get_recommendations.return_value = []
        mock_client = MagicMock()
        mock_client.table().select().in_().order().execute().data = mock_questions
        mock_supabase._get_client.return_value = mock_client

        response = client.get('/api/analytics/user-123', headers={'Authorization': 'Bearer test-token'})
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True
        payload = data['data']
        assert payload['user_id'] == 'user-123'
        assert 'score_trends' in payload
        assert 'skill_trends' in payload
        assert 'difficulty_progression' in payload
        assert 'consistency' in payload
        assert 'repeated_weaknesses' in payload
        assert 'next_practice_recommendations' in payload
        assert payload['score_trends']['total_sessions_analyzed'] == 1

def test_filter_options_endpoint(client):
    """Verifies that /api/analytics/filter-options/<user_id> returns available choices."""
    mock_sessions = [
        {'id': 's1', 'interview_type': 'Frontend', 'start_time': '2026-09-01T00:00:00Z'}
    ]
    mock_questions = [
        {'id': 'q1', 'skill_focus': 'React/CSS', 'difficulty': 'beginner', 'created_at': '2026-09-01T00:00:00Z'}
    ]

    with patch('app.routes.analytics.analytics_service.supabase') as mock_supabase, patch('app.auth.supabase_service._get_client') as mock_auth_client:
        mock_auth_client.return_value.auth.get_user.return_value.user.id = 'user-123'
        mock_auth_client.return_value.auth.get_user.return_value.user.email = 'test@example.com'
        mock_supabase.get_user_sessions.return_value = mock_sessions
        mock_supabase.get_user_skill_profiles.return_value = [{'skill_name': 'React/CSS'}]
        mock_supabase.get_recommendations.return_value = []
        mock_client = MagicMock()
        mock_client.table().select().in_().order().execute().data = mock_questions
        mock_supabase._get_client.return_value = mock_client

        response = client.get('/api/analytics/filter-options/user-123', headers={'Authorization': 'Bearer test-token'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        opts = data['data']
        assert 'Frontend' in opts['interview_types']
        assert 'React/CSS' in opts['skills']
        assert 'beginner' in opts['difficulties']
