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
        self._local_recommendations: Dict[str, Dict[str, Any]] = {}

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

    def get_candidate_skill_profile(self, user_id: str, skill_name: str) -> Optional[Dict[str, Any]]:
        """Get candidate skill profile"""
        try:
            client = self._get_client()
            result = client.table('skill_profiles').select('*').eq('user_id', user_id).eq('skill_name', skill_name).execute()
            
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get skill profile for {user_id}/{skill_name}: {e}")
            return None

    def update_candidate_skill_profile(self, user_id: str, skill_name: str, profile_data: Dict[str, Any]) -> bool:
        """Update or create a candidate skill profile"""
        try:
            client = self._get_client()
            
            # Check if exists
            existing = self.get_candidate_skill_profile(user_id, skill_name)
            
            # Serialize evidence_history if present (Pydantic objects need to be dicts)
            data_to_store = dict(profile_data)
            data_to_store['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            if existing:
                result = client.table('skill_profiles').update(data_to_store).eq('id', existing['id']).execute()
            else:
                data_to_store['id'] = str(uuid.uuid4())
                data_to_store['user_id'] = user_id
                data_to_store['skill_name'] = skill_name
                result = client.table('skill_profiles').insert(data_to_store).execute()
                
            success = len(result.data) > 0
            if success:
                logger.info(f"Skill profile {skill_name} for user {user_id} updated successfully")
            return success
        except Exception as e:
            logger.error(f"Failed to update skill profile for {user_id}/{skill_name}: {e}")
            return False

    def get_user_skill_profiles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all skill profiles for a user"""
        try:
            client = self._get_client()
            result = client.table('skill_profiles').select('*').eq('user_id', user_id).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Failed to get skill profiles for user {user_id}: {e}")
            return []

    def create_recommendations(self, user_id: str, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Persist recommendations to Supabase with in-memory fallback"""
        persisted = []
        for rec in recommendations:
            rec_data = dict(rec)
            rec_id = rec_data.get('id') or str(uuid.uuid4())
            rec_data['id'] = rec_id
            rec_data['user_id'] = user_id
            if 'created_at' not in rec_data:
                rec_data['created_at'] = datetime.now(timezone.utc).isoformat()
            
            # Ensure enums are converted to primitive values
            if hasattr(rec_data.get('status'), 'value'):
                rec_data['status'] = rec_data['status'].value
            if hasattr(rec_data.get('strategy'), 'value'):
                rec_data['strategy'] = rec_data['strategy'].value
            if hasattr(rec_data.get('priority'), 'value'):
                rec_data['priority'] = rec_data['priority'].value
            
            # Always cache in local store for rapid retrieval & resilience
            self._local_recommendations[rec_id] = rec_data
            
            try:
                client = self._get_client()
                result = client.table('recommendations').insert(rec_data).execute()
                if result.data:
                    persisted.append(result.data[0])
                else:
                    persisted.append(rec_data)
            except Exception as e:
                logger.warning(f"Supabase remote insert into 'recommendations' failed (cached locally): {e}")
                persisted.append(rec_data)
                
        return persisted

    def get_recommendations(self, user_id: str, status: Optional[str] = None, strategy: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recommendations for a user with optional status and strategy filters"""
        try:
            client = self._get_client()
            query = client.table('recommendations').select('*').eq('user_id', user_id)
            if status:
                query = query.eq('status', status.upper())
            if strategy:
                query = query.eq('strategy', strategy)
            result = query.order('created_at', desc=True).limit(limit).execute()
            if result.data:
                return result.data
        except Exception as e:
            logger.warning(f"Failed to query remote 'recommendations' table: {e}. Falling back to local cache.")

        # Local cache fallback
        results = [
            r for r in self._local_recommendations.values()
            if r.get('user_id') == user_id
        ]
        if status:
            target_status = status.upper()
            def match_status(val):
                s = str(val.value if hasattr(val, 'value') else val).upper()
                if "." in s:
                    s = s.split(".")[-1]
                return s == target_status
            results = [r for r in results if match_status(r.get('status'))]
        if strategy:
            target_strat = str(strategy.value if hasattr(strategy, 'value') else strategy).lower()
            def match_strat(val):
                s = str(val.value if hasattr(val, 'value') else val).lower()
                if "." in s:
                    s = s.split(".")[-1]
                return s == target_strat
            results = [r for r in results if match_strat(r.get('strategy'))]

        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return results[:limit]

    def get_recommendation(self, recommendation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific recommendation by ID"""
        try:
            client = self._get_client()
            result = client.table('recommendations').select('*').eq('id', recommendation_id).execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            logger.warning(f"Failed to fetch remote recommendation {recommendation_id}: {e}")

        return self._local_recommendations.get(recommendation_id)

    def update_recommendation(self, recommendation_id: str, update_data: Dict[str, Any]) -> bool:
        """Update recommendation status and outcome data"""
        data = dict(update_data)
        data['updated_at'] = datetime.now(timezone.utc).isoformat()

        # Update local cache
        if recommendation_id in self._local_recommendations:
            self._local_recommendations[recommendation_id].update(data)

        try:
            client = self._get_client()
            result = client.table('recommendations').update(data).eq('id', recommendation_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.warning(f"Failed to update remote recommendation {recommendation_id} (updated locally): {e}")
            return recommendation_id in self._local_recommendations

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
