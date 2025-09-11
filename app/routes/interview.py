from flask import Blueprint, request, jsonify, current_app
from app.services.supabase_service import SupabaseService
from app.services.gemini_service import GeminiService
from app.services.security_service import SecurityService
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

interview_bp = Blueprint('interview', __name__)

# Initialize services
supabase_service = SupabaseService()
gemini_service = GeminiService()
security_service = SecurityService()

@interview_bp.route('/start_session', methods=['POST'])
def start_session():
    """Start a new interview session"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': True,
                'message': 'No data provided',
                'code': 'NO_DATA'
            }), 400
        
        # Validate required fields
        user_id = data.get('user_id')
        interview_type = data.get('interview_type')
        
        if not user_id:
            return jsonify({
                'error': True,
                'message': 'user_id is required',
                'code': 'MISSING_USER_ID'
            }), 400
        
        if not interview_type:
            return jsonify({
                'error': True,
                'message': 'interview_type is required',
                'code': 'MISSING_INTERVIEW_TYPE'
            }), 400
        
        # Validate interview type
        valid_types = ['Software Engineer', 'Data Scientist', 'Product Manager', 'DevOps Engineer']
        if interview_type not in valid_types:
            return jsonify({
                'error': True,
                'message': f'Invalid interview_type. Must be one of: {", ".join(valid_types)}',
                'code': 'INVALID_INTERVIEW_TYPE'
            }), 400
        
        # Create session
        result = supabase_service.create_session(user_id, interview_type)
        
        if not result.get('success'):
            logger.error(f"Session creation failed: {result.get('error')}")
            return jsonify({
                'error': True,
                'message': 'Failed to start session',
                'code': 'SESSION_CREATION_FAILED'
            }), 500
        
        session_id = result['session_id']
        
        # Log session start event
        supabase_service.log_event(session_id, 'session_started', {
            'user_id': user_id,
            'interview_type': interview_type,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"Session started successfully: {session_id} for user {user_id}")
        
        return jsonify({
            'error': False,
            'message': 'Session started successfully',
            'data': {
                'session_id': session_id,
                'user_id': user_id,
                'interview_type': interview_type,
                'start_time': result['data']['start_time']
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Unexpected error in start_session: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@interview_bp.route('/get_question', methods=['GET'])
def get_question():
    """Get a new interview question"""
    try:
        session_id = request.args.get('session_id')
        interview_type = request.args.get('interview_type')
        difficulty = request.args.get('difficulty', 'intermediate')
        
        if not session_id:
            return jsonify({
                'error': True,
                'message': 'session_id is required',
                'code': 'MISSING_SESSION_ID'
            }), 400
        
        if not interview_type:
            return jsonify({
                'error': True,
                'message': 'interview_type is required',
                'code': 'MISSING_INTERVIEW_TYPE'
            }), 400
        
        # Validate difficulty level
        valid_difficulties = ['beginner', 'intermediate', 'advanced']
        if difficulty not in valid_difficulties:
            difficulty = 'intermediate'
        
        # Verify session exists and is active
        session = supabase_service.get_session(session_id)
        if not session:
            return jsonify({
                'error': True,
                'message': 'Session not found',
                'code': 'SESSION_NOT_FOUND'
            }), 404
        
        if session.get('status') != 'active':
            return jsonify({
                'error': True,
                'message': 'Session is not active',
                'code': 'SESSION_INACTIVE'
            }), 400
        
        # Generate question using Gemini
        question_text = gemini_service.generate_question(interview_type, difficulty)
        
        # Store question in database
        question_id = supabase_service.store_question(session_id, question_text, interview_type)
        
        if not question_id:
            return jsonify({
                'error': True,
                'message': 'Failed to store question',
                'code': 'QUESTION_STORAGE_FAILED'
            }), 500
        
        # Log question generation event
        supabase_service.log_event(session_id, 'question_generated', {
            'question_id': question_id,
            'difficulty': difficulty,
            'interview_type': interview_type
        })
        
        logger.info(f"Question generated successfully: {question_id} for session {session_id}")
        
        return jsonify({
            'error': False,
            'message': 'Question retrieved successfully',
            'data': {
                'question_id': question_id,
                'question_text': question_text,
                'session_id': session_id,
                'difficulty': difficulty,
                'interview_type': interview_type
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_question: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@interview_bp.route('/submit_answer', methods=['POST'])
def submit_answer():
    """Submit an answer and get evaluation"""
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
        question_id = data.get('question_id')
        answer_text = data.get('answer_text')
        
        if not session_id:
            return jsonify({
                'error': True,
                'message': 'session_id is required',
                'code': 'MISSING_SESSION_ID'
            }), 400
        
        if not question_id:
            return jsonify({
                'error': True,
                'message': 'question_id is required',
                'code': 'MISSING_QUESTION_ID'
            }), 400
        
        if not answer_text:
            return jsonify({
                'error': True,
                'message': 'answer_text is required',
                'code': 'MISSING_ANSWER_TEXT'
            }), 400
        
        # Validate answer length
        if len(answer_text.strip()) < 10:
            return jsonify({
                'error': True,
                'message': 'Answer must be at least 10 characters long',
                'code': 'ANSWER_TOO_SHORT'
            }), 400
        
        # Get session and question details
        session = supabase_service.get_session(session_id)
        if not session:
            return jsonify({
                'error': True,
                'message': 'Session not found',
                'code': 'SESSION_NOT_FOUND'
            }), 404
        
        # Get question details
        questions = supabase_service.get_session_questions(session_id)
        question = next((q for q in questions if q['id'] == question_id), None)
        
        if not question:
            return jsonify({
                'error': True,
                'message': 'Question not found',
                'code': 'QUESTION_NOT_FOUND'
            }), 404
        
        # Evaluate answer using Gemini
        evaluation = gemini_service.evaluate_answer(
            question['question_text'], 
            answer_text, 
            session['interview_type']
        )
        
        # Store answer and evaluation
        success = supabase_service.store_answer(session_id, question_id, answer_text, evaluation)
        
        if not success:
            return jsonify({
                'error': True,
                'message': 'Failed to store answer',
                'code': 'ANSWER_STORAGE_FAILED'
            }), 500
        
        # Update session score
        current_score = session.get('score', 0)
        new_score = (current_score + evaluation.get('score', 0)) / 2  # Average score
        supabase_service.update_session_score(session_id, new_score)
        
        # Log answer submission event
        supabase_service.log_event(session_id, 'answer_submitted', {
            'question_id': question_id,
            'answer_length': len(answer_text),
            'evaluation_score': evaluation.get('score', 0)
        })
        
        # Check for potential anomalies
        if evaluation.get('score', 0) < 30:
            supabase_service.log_anomaly(
                session_id, 
                'low_score', 
                'medium', 
                {'score': evaluation.get('score', 0), 'question_id': question_id}
            )
        
        logger.info(f"Answer submitted successfully for question {question_id}")
        
        return jsonify({
            'error': False,
            'message': 'Answer submitted successfully',
            'data': {
                'question_id': question_id,
                'evaluation': evaluation,
                'session_score': new_score
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in submit_answer: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@interview_bp.route('/session/<session_id>', methods=['GET'])
def get_session_details(session_id):
    """Get detailed information about a session"""
    try:
        # Get session details
        session = supabase_service.get_session(session_id)
        if not session:
            return jsonify({
                'error': True,
                'message': 'Session not found',
                'code': 'SESSION_NOT_FOUND'
            }), 404
        
        # Get session statistics
        stats = supabase_service.get_session_statistics(session_id)
        
        return jsonify({
            'error': False,
            'message': 'Session details retrieved successfully',
            'data': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_session_details: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@interview_bp.route('/end_session/<session_id>', methods=['POST'])
def end_session(session_id):
    """End an interview session"""
    try:
        data = request.get_json() or {}
        final_score = data.get('final_score')
        
        # Get session details
        session = supabase_service.get_session(session_id)
        if not session:
            return jsonify({
                'error': True,
                'message': 'Session not found',
                'code': 'SESSION_NOT_FOUND'
            }), 404
        
        if session.get('status') == 'completed':
            return jsonify({
                'error': True,
                'message': 'Session is already completed',
                'code': 'SESSION_ALREADY_COMPLETED'
            }), 400
        
        # End the session
        success = supabase_service.end_session(session_id, final_score)
        
        if not success:
            return jsonify({
                'error': True,
                'message': 'Failed to end session',
                'code': 'SESSION_END_FAILED'
            }), 500
        
        # Log session end event
        supabase_service.log_event(session_id, 'session_ended', {
            'final_score': final_score,
            'duration_minutes': None  # Could calculate from start_time
        })
        
        logger.info(f"Session {session_id} ended successfully")
        
        return jsonify({
            'error': False,
            'message': 'Session ended successfully',
            'data': {
                'session_id': session_id,
                'status': 'completed',
                'final_score': final_score
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in end_session: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@interview_bp.route('/user/<user_id>/sessions', methods=['GET'])
def get_user_sessions(user_id):
    """Get recent sessions for a user"""
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(max(limit, 1), 50)  # Limit between 1 and 50
        
        sessions = supabase_service.get_user_sessions(user_id, limit)
        
        return jsonify({
            'error': False,
            'message': 'User sessions retrieved successfully',
            'data': {
                'user_id': user_id,
                'sessions': sessions,
                'total_count': len(sessions)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_user_sessions: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@interview_bp.route('/follow_up_question', methods=['POST'])
def get_follow_up_question():
    """Get a follow-up question based on previous Q&A"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': True,
                'message': 'No data provided',
                'code': 'NO_DATA'
            }), 400
        
        question = data.get('question')
        answer = data.get('answer')
        interview_type = data.get('interview_type')
        
        if not all([question, answer, interview_type]):
            return jsonify({
                'error': True,
                'message': 'question, answer, and interview_type are required',
                'code': 'MISSING_REQUIRED_FIELDS'
            }), 400
        
        # Generate follow-up question
        follow_up = gemini_service.generate_follow_up_question(question, answer, interview_type)
        
        return jsonify({
            'error': False,
            'message': 'Follow-up question generated successfully',
            'data': {
                'follow_up_question': follow_up,
                'context': {
                    'original_question': question,
                    'interview_type': interview_type
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_follow_up_question: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@interview_bp.route('/submit_code', methods=['POST'])
def submit_code():
    """Submit code for evaluation"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['session_id', 'question_id', 'code', 'language']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'error': True,
                    'message': f'Missing required field: {field}',
                    'code': 'MISSING_FIELD'
                }), 400
        
        session_id = data['session_id']
        question_id = data['question_id']
        code = data['code']
        language = data['language']
        
        # Validate session
        session = supabase_service.get_session(session_id)
        if not session:
            return jsonify({
                'error': True,
                'message': 'Session not found',
                'code': 'SESSION_NOT_FOUND'
            }), 404
        
        if session.get('status') != 'active':
            return jsonify({
                'error': True,
                'message': 'Session is not active',
                'code': 'SESSION_INACTIVE'
            }), 400
        
        # Get question details
        questions = supabase_service.get_session_questions(session_id)
        question = next((q for q in questions if q['id'] == question_id), None)
        
        if not question:
            return jsonify({
                'error': True,
                'message': 'Question not found',
                'code': 'QUESTION_NOT_FOUND'
            }), 404
        
        # Evaluate code using Gemini
        evaluation = gemini_service.evaluate_code(
            question['question_text'], 
            code, 
            language, 
            session['interview_type']
        )
        
        # Store code submission and evaluation
        success = supabase_service.store_code_submission(
            session_id, 
            question_id, 
            code, 
            language, 
            evaluation
        )
        
        if not success:
            return jsonify({
                'error': True,
                'message': 'Failed to store code submission',
                'code': 'CODE_STORAGE_FAILED'
            }), 500
        
        # Update session score
        current_score = session.get('score', 0)
        new_score = (current_score + evaluation['score']) / 2
        supabase_service.update_session_score(session_id, new_score)
        
        # Log the code submission
        supabase_service.log_event(session_id, 'code_submitted', {
            'question_id': question_id,
            'language': language,
            'code_length': len(code),
            'evaluation_score': evaluation['score']
        })
        
        return jsonify({
            'error': False,
            'message': 'Code submitted successfully',
            'data': {
                'evaluation': evaluation,
                'session_score': new_score
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to submit code: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@interview_bp.route('/security/check', methods=['POST'])
def security_check():
    """Perform security check for cheating detection"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('session_id'):
            return jsonify({
                'error': True,
                'message': 'Missing session_id',
                'code': 'MISSING_SESSION_ID'
            }), 400
        
        session_id = data['session_id']
        security_data = data.get('security_data', {})
        
        # Validate session
        session = supabase_service.get_session(session_id)
        if not session:
            return jsonify({
                'error': True,
                'message': 'Session not found',
                'code': 'SESSION_NOT_FOUND'
            }), 404
        
        # Perform cheating detection
        cheating_detection = security_service.detect_cheating(security_data)
        
        # Log security event if suspicious activity detected
        if cheating_detection['is_cheating']:
            supabase_service.log_anomaly(
                session_id,
                'cheating_detected',
                'high' if cheating_detection['risk_score'] > 0.8 else 'medium',
                {
                    'risk_score': cheating_detection['risk_score'],
                    'anomalies': cheating_detection['anomalies'],
                    'confidence': cheating_detection['confidence']
                }
            )
            
            # Log security event
            supabase_service.log_event(session_id, 'security_alert', {
                'alert_type': 'cheating_detected',
                'risk_score': cheating_detection['risk_score'],
                'anomalies': cheating_detection['anomalies']
            })
        
        return jsonify({
            'error': False,
            'message': 'Security check completed',
            'data': {
                'is_cheating': cheating_detection['is_cheating'],
                'risk_score': cheating_detection['risk_score'],
                'anomalies': cheating_detection['anomalies'],
                'recommendations': cheating_detection['recommendations'],
                'confidence': cheating_detection['confidence']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to perform security check: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@interview_bp.route('/security/report/<session_id>', methods=['GET'])
def get_security_report(session_id: str):
    """Get security report for a session"""
    try:
        # Validate session
        session = supabase_service.get_session(session_id)
        if not session:
            return jsonify({
                'error': True,
                'message': 'Session not found',
                'code': 'SESSION_NOT_FOUND'
            }), 404
        
        # Get security report
        security_report = security_service.get_security_report(session_id)
        
        return jsonify({
            'error': False,
            'message': 'Security report retrieved successfully',
            'data': security_report
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get security report: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@interview_bp.route('/practice/coding', methods=['POST'])
def practice_coding():
    """Generate coding practice questions"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('interview_type'):
            return jsonify({
                'error': True,
                'message': 'Missing interview_type',
                'code': 'MISSING_INTERVIEW_TYPE'
            }), 400
        
        interview_type = data['interview_type']
        difficulty = data.get('difficulty', 'intermediate')
        topic = data.get('topic', 'coding')
        
        # Generate coding question
        question = gemini_service.generate_coding_question(interview_type, difficulty, topic)
        
        return jsonify({
            'error': False,
            'message': 'Coding practice question generated',
            'data': {
                'question': question,
                'interview_type': interview_type,
                'difficulty': difficulty,
                'topic': topic
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to generate coding practice question: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500
