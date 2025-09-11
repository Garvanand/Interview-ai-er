from supabase import create_client, Client
from flask import current_app
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import uuid

logger = logging.getLogger(__name__)

class SupabaseService:
    """Service for interacting with Supabase database"""
    
    def __init__(self):
        self.client: Optional[Client] = None

    def _get_client(self) -> Client:
        """Lazy initialization of Supabase client"""
        if self.client is None:
            try:
                supabase_url = current_app.config.get('SUPABASE_URL')
                supabase_key = current_app.config.get('SUPABASE_KEY')
                
                if not supabase_url or not supabase_key:
                    raise ValueError("Missing Supabase configuration")
                
                self.client = create_client(supabase_url, supabase_key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                raise
        return self.client

    def create_session(self, user_id: str, interview_type: str) -> Dict[str, Any]:
        """Create a new interview session"""
        try:
            client = self._get_client()
            
            session_data = {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'interview_type': interview_type,
                'start_time': datetime.now(timezone.utc).isoformat(),
                'score': 0,
                'status': 'active'
            }
            
            result = client.table('sessions').insert(session_data).execute()
            
            if result.data:
                session = result.data[0]
                logger.info(f"Session created successfully: {session['id']}")
                return {
                    'success': True,
                    'session_id': session['id'],
                    'data': session
                }
            else:
                raise Exception("No data returned from session creation")
                
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        try:
            client = self._get_client()
            result = client.table('sessions').select('*').eq('id', session_id).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    def update_session_score(self, session_id: str, new_score: float) -> bool:
        """Update session score"""
        try:
            client = self._get_client()
            result = client.table('sessions').update({
                'score': new_score,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', session_id).execute()
            
            success = len(result.data) > 0
            if success:
                logger.info(f"Session {session_id} score updated to {new_score}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to update session score: {e}")
            return False

    def end_session(self, session_id: str, final_score: float = None) -> bool:
        """End an interview session"""
        try:
            client = self._get_client()
            
            update_data = {
                'status': 'completed',
                'end_time': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            if final_score is not None:
                update_data['score'] = final_score
            
            result = client.table('sessions').update(update_data).eq('id', session_id).execute()
            
            success = len(result.data) > 0
            if success:
                logger.info(f"Session {session_id} ended successfully")
            return success
            
        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return False

    def store_question(self, session_id: str, question_text: str, interview_type: str) -> Optional[str]:
        """Store a question in the database"""
        try:
            client = self._get_client()
            
            question_data = {
                'id': str(uuid.uuid4()),
                'session_id': session_id,
                'question_text': question_text,
                'interview_type': interview_type,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = client.table('questions').insert(question_data).execute()
            
            if result.data:
                question_id = result.data[0]['id']
                logger.info(f"Question stored successfully: {question_id}")
                return question_id
            return None
            
        except Exception as e:
            logger.error(f"Failed to store question: {e}")
            return None

    def store_answer(self, session_id: str, question_id: str, answer_text: str, evaluation: Dict[str, Any]) -> bool:
        """Store an answer and its evaluation"""
        try:
            client = self._get_client()
            
            answer_data = {
                'answer_text': answer_text,
                'evaluation_score': evaluation.get('score', 0),
                'evaluation_feedback': evaluation.get('feedback', ''),
                'evaluation_details': evaluation,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = client.table('questions').update(answer_data).eq('id', question_id).execute()
            
            success = len(result.data) > 0
            if success:
                logger.info(f"Answer stored successfully for question {question_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to store answer: {e}")
            return False

    def store_code_submission(self, session_id: str, question_id: str, code: str, language: str, evaluation: Dict[str, Any]) -> bool:
        """Store code submission and evaluation"""
        try:
            client = self._get_client()
            
            code_data = {
                'code_text': code,
                'programming_language': language,
                'code_evaluation_score': evaluation.get('score', 0),
                'code_evaluation_details': evaluation,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = client.table('questions').update(code_data).eq('id', question_id).execute()
            
            success = len(result.data) > 0
            if success:
                logger.info(f"Code submission stored successfully for question {question_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to store code submission: {e}")
            return False

    def get_session_questions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all questions for a session"""
        try:
            client = self._get_client()
            result = client.table('questions').select('*').eq('session_id', session_id).order('created_at').execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get questions for session {session_id}: {e}")
            return []

    def log_event(self, session_id: str, event_type: str, details: Dict[str, Any] = None) -> bool:
        """Log a system event"""
        try:
            client = self._get_client()
            
            event_data = {
                'id': str(uuid.uuid4()),
                'session_id': session_id,
                'event_type': event_type,
                'details': details or {},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            result = client.table('logs').insert(event_data).execute()
            
            success = len(result.data) > 0
            if success:
                logger.info(f"Event logged successfully: {event_type}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
            return False

    def log_anomaly(self, session_id: str, anomaly_type: str, severity: str, details: Dict[str, Any] = None) -> bool:
        """Log suspicious behavior or anomalies"""
        try:
            client = self._get_client()
            
            anomaly_data = {
                'id': str(uuid.uuid4()),
                'session_id': session_id,
                'anomaly_type': anomaly_type,
                'severity': severity,
                'details': details or {},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            result = client.table('anomalies').insert(anomaly_data).execute()
            
            success = len(result.data) > 0
            if success:
                logger.warning(f"Anomaly logged: {anomaly_type} (severity: {severity})")
            return success
            
        except Exception as e:
            logger.error(f"Failed to log anomaly: {e}")
            return False

    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sessions for a user"""
        try:
            client = self._get_client()
            result = client.table('sessions').select('*').eq('user_id', user_id).order('start_time', desc=True).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get sessions for user {user_id}: {e}")
            return []

    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a session"""
        try:
            client = self._get_client()
            
            # Get session info
            session_result = client.table('sessions').select('*').eq('id', session_id).execute()
            if not session_result.data:
                return {}
            
            session = session_result.data[0]
            
            # Get questions and answers
            questions_result = client.table('questions').select('*').eq('session_id', session_id).execute()
            questions = questions_result.data if questions_result.data else []
            
            # Calculate statistics
            total_questions = len(questions)
            answered_questions = len([q for q in questions if q.get('answer_text')])
            avg_score = 0
            
            if answered_questions > 0:
                scores = [q.get('evaluation_score', 0) for q in questions if q.get('evaluation_score')]
                avg_score = sum(scores) / len(scores) if scores else 0
            
            # Get events and anomalies
            events_result = client.table('logs').select('*').eq('session_id', session_id).execute()
            events = events_result.data if events_result.data else []
            
            anomalies_result = client.table('anomalies').select('*').eq('session_id', session_id).execute()
            anomalies = anomalies_result.data if anomalies_result.data else []
            
            return {
                'session': session,
                'statistics': {
                    'total_questions': total_questions,
                    'answered_questions': answered_questions,
                    'completion_rate': (answered_questions / total_questions * 100) if total_questions > 0 else 0,
                    'average_score': round(avg_score, 2),
                    'total_events': len(events),
                    'total_anomalies': len(anomalies)
                },
                'questions': questions,
                'events': events,
                'anomalies': anomalies
            }
            
        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            return {}

    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up old completed sessions (for maintenance)"""
        try:
            client = self._get_client()
            cutoff_date = datetime.now(timezone.utc).replace(tzinfo=timezone.utc) - timedelta(days=days_old)
            
            # Get old sessions
            old_sessions = client.table('sessions').select('id').lt('start_time', cutoff_date.isoformat()).eq('status', 'completed').execute()
            
            if not old_sessions.data:
                return 0
            
            deleted_count = 0
            for session in old_sessions.data:
                try:
                    # Delete related records first
                    client.table('questions').delete().eq('session_id', session['id']).execute()
                    client.table('logs').delete().eq('session_id', session['id']).execute()
                    client.table('anomalies').delete().eq('session_id', session['id']).execute()
                    
                    # Delete session
                    client.table('sessions').delete().eq('id', session['id']).execute()
                    deleted_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to cleanup session {session['id']}: {e}")
            
            logger.info(f"Cleaned up {deleted_count} old sessions")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0

    def health_check(self) -> Dict[str, Any]:
        """Check database connectivity and health"""
        try:
            client = self._get_client()
            
            # Test basic connectivity
            result = client.table('sessions').select('count', count='exact').execute()
            
            return {
                'status': 'healthy',
                'database': 'connected',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'database': 'disconnected',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
