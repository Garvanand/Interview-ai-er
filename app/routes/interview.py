from flask import Blueprint, request, jsonify, current_app, g
from app.services.supabase_service import SupabaseService
from app.services.ai import AssessmentEngine, GeminiProvider
from app.services.security_service import SecurityService
from app.services.orchestrator import InterviewOrchestrator
from app.services.execution import CodeSandbox
from app.auth import require_auth, verify_session_ownership
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

interview_bp = Blueprint('interview', __name__)

# Initialize services
supabase_service = SupabaseService()
ai_engine = AssessmentEngine(GeminiProvider())
security_service = SecurityService()
orchestrator = InterviewOrchestrator(supabase_service, ai_engine)
sandbox = CodeSandbox(timeout_seconds=5)

@interview_bp.route('/start_session', methods=['POST'])
@require_auth
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
        
        user_id = g.user_id
        interview_type = data.get('interview_type')
        
        if not interview_type:
            return jsonify({
                'error': True,
                'message': 'interview_type is required',
                'code': 'MISSING_INTERVIEW_TYPE'
            }), 400
        
        # Map and validate interview type
        type_mapping = {
            'Technical': 'Software Engineer',
            'Coding': 'Software Engineer',
            'System Design': 'Software Engineer',
            'Behavioral': 'Software Engineer',
        }
        if interview_type in type_mapping:
            interview_type = type_mapping[interview_type]

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
        
        # Initialize orchestrator state machine
        state = orchestrator.initialize_session(
            session_id=session_id,
            user_id=user_id,
            target_role=interview_type,
            interview_type=interview_type
        )
        
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
                'start_time': result['data']['start_time'],
                'phase': state.phase.value,
                'difficulty': state.difficulty.value,
                'skills': list(state.skills_distribution.keys())
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
@require_auth
def get_question():
    """Get a new interview question backed by stateful orchestrator"""
    try:
        session_id = request.args.get('session_id')
        interview_type = request.args.get('interview_type')
        difficulty = request.args.get('difficulty', 'intermediate')
        
        if not session_id:
            return jsonify({'error': True, 'message': 'session_id is required', 'code': 'MISSING_SESSION_ID'}), 400
            
        if not verify_session_ownership(session_id, g.user_id):
            return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
        
        session = supabase_service.get_session(session_id)
        if not session:
            return jsonify({'error': True, 'message': 'Session not found', 'code': 'SESSION_NOT_FOUND'}), 404
        
        if session.get('status') != 'active':
            return jsonify({'error': True, 'message': 'Session is not active', 'code': 'SESSION_INACTIVE'}), 400
        
        orchestration_result = orchestrator.get_next_question(session_id)
        
        if orchestration_result.get('is_completed'):
            return jsonify({'error': False, 'message': 'Interview has completed', 'data': orchestration_result}), 200
            
        return jsonify({'error': False, 'message': 'Question retrieved successfully', 'data': orchestration_result}), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_question: {e}")
        return jsonify({'error': True, 'message': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

@interview_bp.route('/submit_answer', methods=['POST'])
@require_auth
def submit_answer():
    """Submit an answer and get evaluation"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': True, 'message': 'No data provided', 'code': 'NO_DATA'}), 400
        
        session_id = data.get('session_id')
        question_id = data.get('question_id')
        answer_text = data.get('answer_text')
        
        if not all([session_id, question_id, answer_text]):
            return jsonify({'error': True, 'message': 'Missing fields', 'code': 'MISSING_FIELDS'}), 400
            
        if not verify_session_ownership(session_id, g.user_id):
            return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
        
        if len(answer_text.strip()) < 10:
            return jsonify({'error': True, 'message': 'Answer must be at least 10 characters long', 'code': 'ANSWER_TOO_SHORT'}), 400
        
        session = supabase_service.get_session(session_id)
        if not session or session.get('status') != 'active':
            return jsonify({'error': True, 'message': 'Session not found or inactive', 'code': 'SESSION_INVALID'}), 404
            
        eval_result = orchestrator.record_and_evaluate_answer(
            session_id=session_id,
            question_id=question_id,
            answer_text=answer_text,
            is_code=False
        )
        
        return jsonify({
            'error': False,
            'message': 'Answer submitted successfully',
            'data': {
                'question_id': question_id,
                'evaluation': eval_result['evaluation'],
                'session_score': eval_result['session_score'],
                'current_difficulty': eval_result['current_difficulty'],
                'difficulty_adjusted': eval_result['difficulty_adjusted'],
                'current_phase': eval_result['current_phase'],
                'is_last_question': eval_result['is_last_question'],
                'skills_overview': eval_result['skills_overview']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in submit_answer: {e}")
        return jsonify({'error': True, 'message': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

@interview_bp.route('/session/<session_id>', methods=['GET'])
@require_auth
def get_session_details(session_id):
    """Get detailed information about a session"""
    try:
        if not verify_session_ownership(session_id, g.user_id):
            return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
            
        stats = supabase_service.get_session_statistics(session_id)
        return jsonify({'error': False, 'message': 'Session details retrieved successfully', 'data': stats}), 200
    except Exception as e:
        logger.error(f"Unexpected error in get_session_details: {e}")
        return jsonify({'error': True, 'message': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

@interview_bp.route('/session/<session_id>/state', methods=['GET'])
@require_auth
def get_session_orchestrator_state(session_id):
    """Get backend-authoritative orchestrator state for a session"""
    try:
        if not verify_session_ownership(session_id, g.user_id):
            return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
            
        state_data = orchestrator.get_session_state(session_id)
        return jsonify({'error': False, 'message': 'Session state retrieved successfully', 'data': state_data}), 200
    except Exception as e:
        logger.error(f"Unexpected error in get_session_orchestrator_state: {e}")
        return jsonify({'error': True, 'message': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

@interview_bp.route('/end_session/<session_id>', methods=['POST'])
@require_auth
def end_session(session_id):
    """End an interview session with orchestrated synthesis"""
    try:
        if not verify_session_ownership(session_id, g.user_id):
            return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
            
        session = supabase_service.get_session(session_id)
        if not session:
            return jsonify({'error': True, 'message': 'Session not found', 'code': 'SESSION_NOT_FOUND'}), 404
        
        if session.get('status') == 'completed':
            return jsonify({'error': True, 'message': 'Session is already completed', 'code': 'SESSION_ALREADY_COMPLETED'}), 400
        
        final_result = orchestrator.finalize_interview(session_id)
        return jsonify({'error': False, 'message': 'Session ended successfully', 'data': final_result}), 200
    except Exception as e:
        logger.error(f"Unexpected error in end_session: {e}")
        return jsonify({'error': True, 'message': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

@interview_bp.route('/user/<user_id>/sessions', methods=['GET'])
@require_auth
def get_user_sessions(user_id):
    """Get recent sessions for a user"""
    try:
        if user_id != g.user_id:
            return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
            
        limit = request.args.get('limit', 10, type=int)
        limit = min(max(limit, 1), 50)
        
        sessions = supabase_service.get_user_sessions(user_id, limit)
        return jsonify({
            'error': False,
            'message': 'User sessions retrieved successfully',
            'data': {'user_id': user_id, 'sessions': sessions, 'total_count': len(sessions)}
        }), 200
    except Exception as e:
        logger.error(f"Unexpected error in get_user_sessions: {e}")
        return jsonify({'error': True, 'message': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

@interview_bp.route('/follow_up_question', methods=['POST'])
@require_auth
def get_follow_up_question():
    """Get a follow-up question based on previous Q&A"""
    try:
        data = request.get_json()
        question = data.get('question')
        answer = data.get('answer')
        interview_type = data.get('interview_type')
        
        if not all([question, answer, interview_type]):
            return jsonify({'error': True, 'message': 'Missing fields', 'code': 'MISSING_FIELDS'}), 400
            
        dummy_evaluation = {'overall_score': 70, 'question_id': 'unknown'}
        follow_up_question_data = ai_engine.generate_follow_up_question(question, answer, dummy_evaluation)
        follow_up = follow_up_question_data.get("question_text", str(follow_up_question_data))
        
        return jsonify({
            'error': False,
            'message': 'Follow-up question generated successfully',
            'data': {
                'follow_up_question': follow_up,
                'context': {'original_question': question, 'interview_type': interview_type}
            }
        }), 200
    except Exception as e:
        logger.error(f"Unexpected error in get_follow_up_question: {e}")
        return jsonify({'error': True, 'message': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

@interview_bp.route('/run_code', methods=['POST'])
@require_auth
def run_code():
    """Execute code without saving it as a submission"""
    try:
        data = request.get_json()
        code = data.get('code')
        language = data.get('language')
        
        if not all([code, language]):
            return jsonify({'error': True, 'message': 'Missing fields', 'code': 'MISSING_FIELDS'}), 400
            
        result = sandbox.execute(code, language)
        return jsonify({'error': False, 'message': 'Code executed', 'data': result}), 200
    except Exception as e:
        logger.error(f"Failed to run code: {e}")
        return jsonify({'error': True, 'message': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

@interview_bp.route('/submit_code', methods=['POST'])
@require_auth
def submit_code():
    """Submit code for evaluation"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        question_id = data.get('question_id')
        code = data.get('code')
        language = data.get('language')
        
        if not all([session_id, question_id, code, language]):
            return jsonify({'error': True, 'message': 'Missing fields', 'code': 'MISSING_FIELDS'}), 400
            
        if not verify_session_ownership(session_id, g.user_id):
            return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
            
        session = supabase_service.get_session(session_id)
        if not session or session.get('status') != 'active':
            return jsonify({'error': True, 'message': 'Session not active', 'code': 'SESSION_INACTIVE'}), 400
            
        eval_result = orchestrator.record_and_evaluate_answer(
            session_id=session_id,
            question_id=question_id,
            answer_text=code,
            is_code=True,
            language=language
        )
        
        return jsonify({
            'error': False,
            'message': 'Code submitted successfully',
            'data': {
                'evaluation': eval_result['evaluation'],
                'session_score': eval_result['session_score'],
                'current_difficulty': eval_result['current_difficulty'],
                'current_phase': eval_result['current_phase'],
                'is_last_question': eval_result['is_last_question']
            }
        }), 200
    except Exception as e:
        logger.error(f"Failed to submit code: {e}")
        return jsonify({'error': True, 'message': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

@interview_bp.route('/security/check', methods=['POST'])
@require_auth
def security_check():
    """Perform security check for cheating detection"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        security_data = data.get('security_data', {})
        
        if not session_id:
            return jsonify({'error': True, 'message': 'Missing session_id', 'code': 'MISSING_SESSION_ID'}), 400
            
        if not verify_session_ownership(session_id, g.user_id):
            return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
            
        events = security_data.get('events', [])
        if not events and 'type' in security_data:
            events = [security_data]
            
        report = security_service.process_raw_events(session_id, events)
        
        if report.review_recommended:
            supabase_service.log_anomaly(
                session_id,
                'session_integrity_flag',
                'high' if report.aggregation_score > 0.8 else 'medium',
                {
                    'aggregation_score': report.aggregation_score,
                    'signals': [sig.model_dump() for sig in report.signals],
                    'confidence': report.confidence_in_assessment
                }
            )
            
        return jsonify({
            'error': False,
            'message': 'Integrity check completed',
            'data': {
                'review_recommended': report.review_recommended,
                'aggregation_score': report.aggregation_score,
                'signals': [sig.model_dump() for sig in report.signals],
                'summary': report.summary,
                'confidence': report.confidence_in_assessment
            }
        }), 200
    except Exception as e:
        logger.error(f"Failed to perform security check: {e}")
        return jsonify({'error': True, 'message': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

@interview_bp.route('/security/report/<session_id>', methods=['GET'])
@require_auth
def get_security_report(session_id: str):
    """Get security report for a session"""
    if not verify_session_ownership(session_id, g.user_id):
        return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
    return jsonify({'error': True, 'message': 'Not implemented', 'code': 'NOT_IMPLEMENTED'}), 501

@interview_bp.route('/practice/coding', methods=['POST'])
@require_auth
def practice_coding():
    """Generate coding practice questions"""
    try:
        data = request.get_json()
        interview_type = data.get('interview_type')
        if not interview_type:
            return jsonify({'error': True, 'message': 'Missing interview_type', 'code': 'MISSING_INTERVIEW_TYPE'}), 400
            
        difficulty = data.get('difficulty', 'intermediate')
        topic = data.get('topic', 'coding')
        
        question_data = ai_engine.generate_question("coding", difficulty, topic=topic)
        question = question_data.get("question_text", str(question_data))
        
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
        return jsonify({'error': True, 'message': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500
