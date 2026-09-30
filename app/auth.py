from functools import wraps
from flask import request, jsonify, g
import logging
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)
supabase_service = SupabaseService()

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning("Missing or invalid Authorization header")
            return jsonify({'success': False, 'message': 'Missing or invalid Authorization header'}), 401
            
        token = auth_header.split(' ')[1]
        try:
            client = supabase_service._get_client()
            # Validate token and get user
            user_res = client.auth.get_user(token)
            if not user_res or not user_res.user:
                return jsonify({'success': False, 'message': 'Invalid or expired token'}), 401
                
            g.user_id = user_res.user.id
            g.user_email = user_res.user.email
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({'success': False, 'message': 'Authentication failed'}), 401
            
        return f(*args, **kwargs)
    return decorated

def verify_session_ownership(session_id: str, user_id: str) -> bool:
    """Check if the session belongs to the given user"""
    session = supabase_service.get_session(session_id)
    if not session:
        return False
    return session.get('user_id') == user_id
