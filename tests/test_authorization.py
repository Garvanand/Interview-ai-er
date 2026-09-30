import pytest
import os
from unittest.mock import patch, MagicMock

os.environ.setdefault('SUPABASE_URL', 'https://dummy.supabase.co')
os.environ.setdefault('SUPABASE_KEY', 'dummy-key')
os.environ.setdefault('GEMINI_API_KEY', 'dummy-gemini-key')
from app import create_app
from flask import json

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def mock_auth_user(client_mock, user_id="test_user_id"):
    user_mock = MagicMock()
    user_mock.user.id = user_id
    user_mock.user.email = "test@example.com"
    client_mock.auth.get_user.return_value = user_mock
    return client_mock

@patch('app.auth.supabase_service._get_client')
def test_no_auth_header(mock_get_client, client):
    """Test that missing auth header returns 401"""
    response = client.post('/api/start_session', json={
        'interview_type': 'Technical'
    })
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['message'] == 'Missing or invalid Authorization header'

@patch('app.auth.supabase_service._get_client')
def test_invalid_auth_header(mock_get_client, client):
    """Test that invalid auth header format returns 401"""
    response = client.post('/api/start_session', 
        json={'interview_type': 'Technical'},
        headers={'Authorization': 'InvalidFormatToken'}
    )
    assert response.status_code == 401

@patch('app.auth.supabase_service._get_client')
def test_auth_success(mock_get_client, client):
    """Test that valid auth header allows request (though it might fail later due to DB mock)"""
    mock_client = MagicMock()
    mock_auth_user(mock_client, "user_123")
    mock_get_client.return_value = mock_client
    
    # Use patch on create_session to isolate the auth test
    with patch('app.routes.interview.supabase_service.create_session') as mock_create:
        mock_create.return_value = {'success': True, 'session_id': 'session_123', 'data': {'start_time': 'now'}}
        with patch('app.routes.interview.orchestrator.initialize_session') as mock_init:
            mock_init.return_value = MagicMock(phase=MagicMock(value="INITIALIZING"), difficulty=MagicMock(value="intermediate"), skills_distribution={})
            response = client.post('/api/start_session', 
                json={'interview_type': 'Technical'},
                headers={'Authorization': 'Bearer valid_token'}
            )
            assert response.status_code == 201
            mock_create.assert_called_with("user_123", "Software Engineer")

@patch('app.auth.supabase_service.get_session')
@patch('app.auth.supabase_service._get_client')
def test_cross_user_access(mock_get_client, mock_get_session, client):
    """Test that accessing another user's session returns 403"""
    # Setup auth mock for User A
    mock_client = MagicMock()
    mock_auth_user(mock_client, "user_A")
    mock_get_client.return_value = mock_client
    
    # Setup session mock belonging to User B
    mock_get_session.return_value = {'id': 'session_B', 'user_id': 'user_B'}
    
    response = client.get('/api/session/session_B',
        headers={'Authorization': 'Bearer valid_token_user_A'}
    )
    
    assert response.status_code == 403
    data = json.loads(response.data)
    assert data['error'] is True
    assert data['message'] == 'Unauthorized'

@patch('app.auth.supabase_service.get_session')
@patch('app.auth.supabase_service._get_client')
def test_own_session_access(mock_get_client, mock_get_session, client):
    """Test that accessing own session proceeds"""
    # Setup auth mock for User A
    mock_client = MagicMock()
    mock_auth_user(mock_client, "user_A")
    mock_get_client.return_value = mock_client
    
    # Setup session mock belonging to User A
    mock_get_session.return_value = {'id': 'session_A', 'user_id': 'user_A'}
    
    with patch('app.routes.interview.supabase_service.get_session_statistics') as mock_stats:
        mock_stats.return_value = {}
        response = client.get('/api/session/session_A',
            headers={'Authorization': 'Bearer valid_token_user_A'}
        )
        
        assert response.status_code == 200

@patch('app.auth.supabase_service._get_client')
def test_path_user_id_mismatch(mock_get_client, client):
    """Test that path user_id mismatch returns 403 (for intelligence route)"""
    mock_client = MagicMock()
    mock_auth_user(mock_client, "user_A")
    mock_get_client.return_value = mock_client
    
    response = client.get('/api/intelligence/skills/user_B',
        headers={'Authorization': 'Bearer valid_token_user_A'}
    )
    
    assert response.status_code == 403
    data = json.loads(response.data)
    assert data['message'] == 'Unauthorized'
