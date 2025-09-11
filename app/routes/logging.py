from flask import Blueprint, request, jsonify
from app.services.supabase_service import SupabaseService
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

logging_bp = Blueprint('logging', __name__)

# Initialize service
supabase_service = SupabaseService()

@logging_bp.route('/log_event', methods=['POST'])
def log_event():
    """Log a system event"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': True,
                'message': 'No data provided',
                'code': 'NO_DATA'
            }), 400
        
        # Validate required fields
        session_id = data.get('session_id')
        event_type = data.get('event_type')
        
        if not session_id:
            return jsonify({
                'error': True,
                'message': 'session_id is required',
                'code': 'MISSING_SESSION_ID'
            }), 400
        
        if not event_type:
            return jsonify({
                'error': True,
                'message': 'event_type is required',
                'code': 'MISSING_EVENT_TYPE'
            }), 400
        
        # Validate event type
        valid_event_types = [
            'session_started', 'session_ended', 'question_generated', 
            'answer_submitted', 'evaluation_completed', 'user_action',
            'system_event', 'error_occurred', 'performance_metric'
        ]
        
        if event_type not in valid_event_types:
            return jsonify({
                'error': True,
                'message': f'Invalid event_type. Must be one of: {", ".join(valid_event_types)}',
                'code': 'INVALID_EVENT_TYPE'
            }), 400
        
        # Optional details
        details = data.get('details', {})
        
        # Log the event
        success = supabase_service.log_event(session_id, event_type, details)
        
        if not success:
            return jsonify({
                'error': True,
                'message': 'Failed to log event',
                'code': 'EVENT_LOGGING_FAILED'
            }), 500
        
        logger.info(f"Event logged successfully: {event_type} for session {session_id}")
        
        return jsonify({
            'error': False,
            'message': 'Event logged successfully',
            'data': {
                'event_type': event_type,
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in log_event: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@logging_bp.route('/log_anomaly', methods=['POST'])
def log_anomaly():
    """Log suspicious behavior or anomalies"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': True,
                'message': 'No data provided',
                'code': 'NO_DATA'
            }), 400
        
        # Validate required fields
        session_id = data.get('session_id')
        anomaly_type = data.get('anomaly_type')
        severity = data.get('severity')
        
        if not session_id:
            return jsonify({
                'error': True,
                'message': 'session_id is required',
                'code': 'MISSING_SESSION_ID'
            }), 400
        
        if not anomaly_type:
            return jsonify({
                'error': True,
                'message': 'anomaly_type is required',
                'code': 'MISSING_ANOMALY_TYPE'
            }), 400
        
        if not severity:
            return jsonify({
                'error': True,
                'message': 'severity is required',
                'code': 'MISSING_SEVERITY'
            }), 400
        
        # Validate anomaly type
        valid_anomaly_types = [
            'low_score', 'rapid_answers', 'copy_paste', 'multiple_sessions',
            'unusual_pattern', 'system_abuse', 'performance_issue'
        ]
        
        if anomaly_type not in valid_anomaly_types:
            return jsonify({
                'error': True,
                'message': f'Invalid anomaly_type. Must be one of: {", ".join(valid_anomaly_types)}',
                'code': 'INVALID_ANOMALY_TYPE'
            }), 400
        
        # Validate severity
        valid_severities = ['low', 'medium', 'high', 'critical']
        if severity not in valid_severities:
            return jsonify({
                'error': True,
                'message': f'Invalid severity. Must be one of: {", ".join(valid_severities)}',
                'code': 'INVALID_SEVERITY'
            }), 400
        
        # Optional details
        details = data.get('details', {})
        
        # Log the anomaly
        success = supabase_service.log_anomaly(session_id, anomaly_type, severity, details)
        
        if not success:
            return jsonify({
                'error': True,
                'message': 'Failed to log anomaly',
                'code': 'ANOMALY_LOGGING_FAILED'
            }), 500
        
        logger.warning(f"Anomaly logged: {anomaly_type} (severity: {severity}) for session {session_id}")
        
        return jsonify({
            'error': False,
            'message': 'Anomaly logged successfully',
            'data': {
                'anomaly_type': anomaly_type,
                'severity': severity,
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in log_anomaly: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@logging_bp.route('/events/<session_id>', methods=['GET'])
def get_session_events(session_id):
    """Get all events for a specific session"""
    try:
        # Get events from database
        # Note: This would need to be implemented in SupabaseService
        # For now, we'll return a placeholder response
        
        return jsonify({
            'error': False,
            'message': 'Session events retrieved successfully',
            'data': {
                'session_id': session_id,
                'events': [],
                'total_count': 0
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_session_events: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@logging_bp.route('/anomalies/<session_id>', methods=['GET'])
def get_session_anomalies(session_id):
    """Get all anomalies for a specific session"""
    try:
        # Get anomalies from database
        # Note: This would need to be implemented in SupabaseService
        # For now, we'll return a placeholder response
        
        return jsonify({
            'error': False,
            'message': 'Session anomalies retrieved successfully',
            'data': {
                'session_id': session_id,
                'anomalies': [],
                'total_count': 0
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_session_anomalies: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@logging_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check database health
        db_health = supabase_service.health_check()
        
        # Overall health status
        overall_status = 'healthy' if db_health.get('status') == 'healthy' else 'unhealthy'
        
        return jsonify({
            'error': False,
            'message': 'Service is healthy',
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'database': db_health.get('status', 'unknown'),
                'api': 'healthy'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'error': False,
            'message': 'Service is unhealthy',
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'database': 'unknown',
                'api': 'unhealthy'
            }
        }), 503

@logging_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """Get system metrics and statistics"""
    try:
        # This would typically include:
        # - Total sessions
        # - Active sessions
        # - Questions generated
        # - Answers evaluated
        # - System performance metrics
        
        return jsonify({
            'error': False,
            'message': 'Metrics retrieved successfully',
            'data': {
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': {
                    'total_sessions': 0,
                    'active_sessions': 0,
                    'total_questions': 0,
                    'total_answers': 0,
                    'system_uptime': '0 seconds'
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_metrics: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500
