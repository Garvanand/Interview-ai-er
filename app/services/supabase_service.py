import os
import json
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
from flask import current_app

logger = logging.getLogger(__name__)

class SupabaseService:
    """Service for interacting with Supabase database (New Architecture)"""
    _shared_recommendations: Dict[str, Dict[str, Any]] = {}
    _shared_sessions: Dict[str, Dict[str, Any]] = {}
    _shared_questions: Dict[str, List[Dict[str, Any]]] = {}
    _shared_events: Dict[str, List[Dict[str, Any]]] = {}
    _shared_anomalies: Dict[str, List[Dict[str, Any]]] = {}
    _shared_skill_profiles: Dict[str, Dict[str, Any]] = {}
    _shared_question_skills: Dict[str, Dict[str, Any]] = {}
    _cache_file: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        ".local_storage_cache.json"
    )
    _cache_loaded: bool = False
    _remote_available: Optional[bool] = None

    def __init__(self):
        self.client: Optional[Client] = None
        self._local_recommendations = SupabaseService._shared_recommendations
        self._local_sessions = SupabaseService._shared_sessions
        self._local_questions = SupabaseService._shared_questions
        self._local_events = SupabaseService._shared_events
        self._local_anomalies = SupabaseService._shared_anomalies
        self._local_skill_profiles = SupabaseService._shared_skill_profiles
        self._local_question_skills = SupabaseService._shared_question_skills
        self._ensure_cache_loaded()

    @classmethod
    def _ensure_cache_loaded(cls):
        if cls._cache_loaded:
            return
        cls._cache_loaded = True
        try:
            if os.path.exists(cls._cache_file):
                with open(cls._cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cls._shared_sessions.update(data.get("sessions", {}))
                    cls._shared_questions.update(data.get("questions", {}))
                    cls._shared_events.update(data.get("events", {}))
                    cls._shared_anomalies.update(data.get("anomalies", {}))
                    cls._shared_skill_profiles.update(data.get("skill_profiles", {}))
                    cls._shared_recommendations.update(data.get("recommendations", {}))
                    cls._shared_question_skills.update(data.get("question_skills", {}))
                logger.info(f"Loaded {len(cls._shared_sessions)} sessions from local storage cache.")
        except Exception as e:
            logger.warning(f"Failed to load local storage cache: {e}")

    @classmethod
    def _save_cache_to_disk(cls):
        try:
            cache_data = {
                "sessions": cls._shared_sessions,
                "questions": cls._shared_questions,
                "events": cls._shared_events,
                "anomalies": cls._shared_anomalies,
                "skill_profiles": cls._shared_skill_profiles,
                "recommendations": cls._shared_recommendations,
                "question_skills": cls._shared_question_skills,
            }
            tmp_file = cls._cache_file + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
            if os.path.exists(cls._cache_file):
                os.replace(tmp_file, cls._cache_file)
            else:
                os.rename(tmp_file, cls._cache_file)
        except Exception as e:
            logger.warning(f"Failed to save local storage cache: {e}")

    def is_fallback_mode(self) -> bool:
        """Returns True if remote Supabase database tables are not accessible or configured"""
        return SupabaseService._remote_available is False

    def create_local_session(self, session_id: str, user_id: str, interview_type: str = "Software Engineer") -> Dict[str, Any]:
        """Creates or registers a local session (useful for state recovery or offline development)"""
        session_data = {
            'id': session_id,
            'user_id': user_id,
            'interview_type': interview_type,
            'start_time': datetime.now(timezone.utc).isoformat(),
            'score': 0,
            'status': 'active'
        }
        self._local_sessions[session_id] = session_data
        self._save_cache_to_disk()
        logger.info(f"Local session registered/restored: {session_id} for user {user_id}")
        return session_data

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
        session_data = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'interview_type': interview_type,
            'start_time': datetime.now(timezone.utc).isoformat(),
            'score': 0,
            'status': 'active'
        }
        try:
            client = self._get_client()
            result = client.table('interview_sessions').insert(session_data).execute()
            if result.data:
                SupabaseService._remote_available = True
                session = result.data[0]
                self._local_sessions[session['id']] = session
                self._save_cache_to_disk()
                logger.info(f"Session created successfully: {session['id']}")
                return {
                    'success': True,
                    'session_id': session['id'],
                    'data': session
                }
            else:
                raise Exception("No data returned from session creation")
        except Exception as e:
            err_str = str(e)
            if "PGRST205" in err_str or "Could not find the table" in err_str or "interview_sessions" in err_str:
                SupabaseService._remote_available = False
                logger.warning(f"Supabase remote insert failed ({e}). Falling back to local in-memory session.")
                self._local_sessions[session_data['id']] = session_data
                self._save_cache_to_disk()
                return {
                    'success': True,
                    'session_id': session_data['id'],
                    'data': session_data
                }
            logger.error(f"Failed to create session: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        try:
            client = self._get_client()
            result = client.table('interview_sessions').select('*').eq('id', session_id).execute()
            if result.data:
                SupabaseService._remote_available = True
                return result.data[0]
            SupabaseService._remote_available = True
        except Exception as e:
            err_str = str(e)
            if "PGRST205" in err_str or "Could not find the table" in err_str or "interview_sessions" in err_str:
                SupabaseService._remote_available = False
            logger.warning(f"Failed to get session {session_id} from remote: {e}")
        return self._local_sessions.get(session_id)


    def update_session_score(self, session_id: str, new_score: float) -> bool:
        """Update session score"""
        if session_id in self._local_sessions:
            self._local_sessions[session_id]['score'] = new_score
            self._local_sessions[session_id]['updated_at'] = datetime.now(timezone.utc).isoformat()
            self._save_cache_to_disk()
        try:
            client = self._get_client()
            result = client.table('interview_sessions').update({
                'score': new_score,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', session_id).execute()
            success = len(result.data) > 0
            if success:
                logger.info(f"Session {session_id} score updated to {new_score}")
            return success
        except Exception as e:
            logger.warning(f"Failed to update session score remotely: {e}")
            return session_id in self._local_sessions

    def end_session(self, session_id: str, final_score: float = None) -> bool:
        """End an interview session"""
        if session_id in self._local_sessions:
            self._local_sessions[session_id]['status'] = 'COMPLETED'
            self._local_sessions[session_id]['end_time'] = datetime.now(timezone.utc).isoformat()
            if final_score is not None:
                self._local_sessions[session_id]['score'] = final_score
            self._save_cache_to_disk()
        try:
            client = self._get_client()
            update_data = {
                'status': 'COMPLETED',
                'end_time': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            if final_score is not None:
                update_data['score'] = final_score
            result = client.table('interview_sessions').update(update_data).eq('id', session_id).execute()
            success = len(result.data) > 0
            if success:
                logger.info(f"Session {session_id} ended successfully")
            return success
        except Exception as e:
            logger.warning(f"Failed to end session {session_id} remotely: {e}")
            return session_id in self._local_sessions

    def store_question(self, session_id: str, question_text: str, interview_type: str = "technical") -> Optional[str]:
        """Store a question in the database"""
        question_data = {
            'id': str(uuid.uuid4()),
            'session_id': session_id,
            'question_text': question_text,
            'question_type': interview_type or 'technical',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        if session_id not in self._local_questions:
            self._local_questions[session_id] = []
        self._local_questions[session_id].append(question_data)
        self._save_cache_to_disk()

        try:
            client = self._get_client()
            result = client.table('interview_questions').insert(question_data).execute()
            if result.data:
                question_id = result.data[0]['id']
                logger.info(f"Question stored successfully: {question_id}")
                return question_id
        except Exception as e:
            logger.warning(f"Failed to store question remotely: {e}. Stored in local fallback cache.")
        return question_data['id']

    def store_answer(self, session_id: str, question_id: str, answer_text: str, evaluation: Dict[str, Any]) -> bool:
        """Store an answer and its evaluation in normalized tables"""
        if session_id in self._local_questions:
            for q in self._local_questions[session_id]:
                if q.get('id') == question_id:
                    q['answer_text'] = answer_text
                    q['evaluation_score'] = evaluation.get('score', 0)
                    q['evaluation_feedback'] = evaluation.get('feedback', '')
                    q['evaluation_details'] = evaluation
            self._save_cache_to_disk()
        try:
            client = self._get_client()
            response_id = str(uuid.uuid4())
            response_data = {
                'id': response_id,
                'question_id': question_id,
                'response_text': answer_text,
                'submitted_at': datetime.now(timezone.utc).isoformat()
            }
            client.table('responses').insert(response_data).execute()
            
            eval_data = {
                'id': str(uuid.uuid4()),
                'response_id': response_id,
                'score': evaluation.get('score', 0),
                'feedback': evaluation.get('feedback', ''),
                'evaluation_details': evaluation,
                'status': 'COMPLETED'
            }
            client.table('evaluations').insert(eval_data).execute()
            logger.info(f"Answer stored successfully for question {question_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to store answer remotely: {e}. Stored in local fallback cache.")
            return True

    def store_code_submission(self, session_id: str, question_id: str, code: str, language: str, evaluation: Dict[str, Any]) -> bool:
        """Store code submission and evaluation in normalized tables"""
        if session_id in self._local_questions:
            for q in self._local_questions[session_id]:
                if q.get('id') == question_id:
                    q['code_text'] = code
                    q['code_language'] = language
                    q['code_evaluation_score'] = evaluation.get('score', 0)
                    q['code_evaluation_feedback'] = evaluation.get('feedback', '')
                    q['code_evaluation_details'] = evaluation
            self._save_cache_to_disk()
        try:
            client = self._get_client()
            
            # 1. Insert code submission
            submission_id = str(uuid.uuid4())
            code_data = {
                'id': submission_id,
                'question_id': question_id,
                'code_text': code,
                'programming_language': language,
                'submitted_at': datetime.now(timezone.utc).isoformat()
            }
            client.table('code_submissions').insert(code_data).execute()
            
            # 2. Insert execution run details
            exec_data = {
                'id': str(uuid.uuid4()),
                'code_submission_id': submission_id,
                'status': 'COMPLETED',
                'stdout': evaluation.get('stdout', ''),
                'stderr': evaluation.get('stderr', '')
            }
            client.table('execution_runs').insert(exec_data).execute()
            
            # Since evaluations are also expected for code, we mock a response + evaluation
            # so standard flows don't break, or we just rely on code_submissions for analytics.
            response_id = str(uuid.uuid4())
            client.table('responses').insert({
                'id': response_id,
                'question_id': question_id,
                'response_text': code,
                'submitted_at': datetime.now(timezone.utc).isoformat()
            }).execute()
            
            client.table('evaluations').insert({
                'id': str(uuid.uuid4()),
                'response_id': response_id,
                'score': evaluation.get('score', 0),
                'feedback': evaluation.get('feedback', ''),
                'evaluation_details': evaluation,
                'status': 'COMPLETED'
            }).execute()
            
            logger.info(f"Code submission stored successfully for question {question_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to store code submission remotely: {e}. Stored in local fallback cache.")
            return True

    def get_session_questions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all questions for a session, including legacy format compatibility"""
        try:
            client = self._get_client()
            # Join questions with responses and evaluations
            result = client.table('interview_questions').select(
                '*, responses(*, evaluations(*))'
            ).eq('session_id', session_id).order('created_at').execute()
            
            if result.data:
                questions = []
                for q in result.data:
                    q_mapped = dict(q)
                    if q.get('responses') and len(q['responses']) > 0:
                        latest_response = q['responses'][-1]
                        q_mapped['answer_text'] = latest_response.get('response_text')
                        if latest_response.get('evaluations') and len(latest_response['evaluations']) > 0:
                            latest_eval = latest_response['evaluations'][-1]
                            q_mapped['evaluation_score'] = latest_eval.get('score')
                            q_mapped['evaluation_feedback'] = latest_eval.get('feedback')
                            q_mapped['evaluation_details'] = latest_eval.get('evaluation_details')
                    questions.append(q_mapped)
                return questions
        except Exception as e:
            logger.warning(f"Failed to get questions remotely for session {session_id}: {e}")
        return self._local_questions.get(session_id, [])

    def log_event(self, session_id: str, event_type: str, details: Dict[str, Any] = None) -> bool:
        """Log a system event to session_events"""
        event_data = {
            'id': str(uuid.uuid4()),
            'session_id': session_id,
            'event_type': event_type,
            'event_data': details or {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        if session_id not in self._local_events:
            self._local_events[session_id] = []
        self._local_events[session_id].append(event_data)
        self._save_cache_to_disk()
        try:
            client = self._get_client()
            result = client.table('session_events').insert(event_data).execute()
            return len(result.data) > 0
        except Exception as e:
            return True

    def log_anomaly(self, session_id: str, anomaly_type: str, severity: str, details: Dict[str, Any] = None) -> bool:
        """Log suspicious behavior to integrity_events"""
        anomaly_data = {
            'id': str(uuid.uuid4()),
            'session_id': session_id,
            'event_type': anomaly_type,
            'severity': severity,
            'evidence_details': details or {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        if session_id not in self._local_anomalies:
            self._local_anomalies[session_id] = []
        self._local_anomalies[session_id].append(anomaly_data)
        self._save_cache_to_disk()
        try:
            client = self._get_client()
            result = client.table('integrity_events').insert(anomaly_data).execute()
            return len(result.data) > 0
        except Exception as e:
            return True

    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sessions for a user"""
        try:
            client = self._get_client()
            result = client.table('interview_sessions').select('*').eq('user_id', user_id).order('start_time', desc=True).limit(limit).execute()
            if result.data:
                return result.data
        except Exception as e:
            logger.warning(f"Failed to get sessions remotely for user {user_id}: {e}")
        local_user_sessions = [s for s in self._local_sessions.values() if s.get('user_id') == user_id]
        return sorted(local_user_sessions, key=lambda s: s.get('start_time', ''), reverse=True)[:limit]

    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a session with full local fallback"""
        session = None
        try:
            client = self._get_client()
            session_result = client.table('interview_sessions').select('*').eq('id', session_id).execute()
            if session_result.data:
                session = session_result.data[0]
        except Exception as e:
            logger.warning(f"Failed to get session remotely in get_session_statistics: {e}")

        if not session:
            session = self._local_sessions.get(session_id)

        if not session:
            return {}

        questions = self.get_session_questions(session_id)
        total_questions = len(questions)
        answered_questions = len([q for q in questions if q.get('answer_text') or q.get('code_text')])
        avg_score = 0
        if answered_questions > 0:
            scores = [q.get('evaluation_score') or q.get('code_evaluation_score', 0) for q in questions if q.get('evaluation_score') or q.get('code_evaluation_score')]
            avg_score = sum(scores) / len(scores) if scores else 0

        events = []
        try:
            client = self._get_client()
            events_result = client.table('session_events').select('*').eq('session_id', session_id).execute()
            events = events_result.data if events_result.data else []
        except Exception:
            events = self._local_events.get(session_id, [])

        anomalies = []
        try:
            client = self._get_client()
            anomalies_result = client.table('integrity_events').select('*').eq('session_id', session_id).execute()
            anomalies = anomalies_result.data if anomalies_result.data else []
        except Exception:
            anomalies = self._local_anomalies.get(session_id, [])

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


    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up old completed sessions"""
        try:
            client = self._get_client()
            cutoff_date = datetime.now(timezone.utc).replace(tzinfo=timezone.utc) - timedelta(days=days_old)
            
            old_sessions = client.table('interview_sessions').select('id').lt('start_time', cutoff_date.isoformat()).eq('status', 'COMPLETED').execute()
            
            if not old_sessions.data:
                return 0
            
            deleted_count = 0
            for session in old_sessions.data:
                try:
                    # RLS and ON DELETE CASCADE should handle the rest
                    client.table('interview_sessions').delete().eq('id', session['id']).execute()
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
        key = f"{user_id}:{skill_name}"
        try:
            client = self._get_client()
            result = client.table('candidate_skill_profiles').select('*').eq('user_id', user_id).eq('skill_name', skill_name).execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            logger.warning(f"Failed to get skill profile remotely: {e}")
        return self._local_skill_profiles.get(key)

    def update_candidate_skill_profile(self, user_id: str, skill_name: str, profile_data: Dict[str, Any]) -> bool:
        """Update or create a candidate skill profile"""
        key = f"{user_id}:{skill_name}"
        data_to_store = dict(profile_data)
        data_to_store['id'] = self._local_skill_profiles.get(key, {}).get('id') or str(uuid.uuid4())
        data_to_store['user_id'] = user_id
        data_to_store['skill_name'] = skill_name
        data_to_store['updated_at'] = datetime.now(timezone.utc).isoformat()
        self._local_skill_profiles[key] = data_to_store
        self._save_cache_to_disk()
        try:
            client = self._get_client()
            existing = self.get_candidate_skill_profile(user_id, skill_name)
            if existing and existing.get('id') != data_to_store['id']:
                result = client.table('candidate_skill_profiles').update(data_to_store).eq('id', existing['id']).execute()
            else:
                result = client.table('candidate_skill_profiles').insert(data_to_store).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.warning(f"Failed to update skill profile remotely: {e}. Stored locally.")
            return True

    def get_user_skill_profiles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all skill profiles for a user"""
        try:
            client = self._get_client()
            result = client.table('candidate_skill_profiles').select('*').eq('user_id', user_id).execute()
            if result.data:
                return result.data
        except Exception as e:
            logger.warning(f"Failed to get skill profiles remotely: {e}")
        return [p for p in self._local_skill_profiles.values() if p.get('user_id') == user_id]

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
            
            if hasattr(rec_data.get('status'), 'value'):
                rec_data['status'] = rec_data['status'].value
            if hasattr(rec_data.get('strategy'), 'value'):
                rec_data['strategy'] = rec_data['strategy'].value
            if hasattr(rec_data.get('priority'), 'value'):
                rec_data['priority'] = rec_data['priority'].value
            
            self._local_recommendations[rec_id] = rec_data
            
            try:
                client = self._get_client()
                result = client.table('recommendations').insert(rec_data).execute()
                if result.data:
                    persisted.append(result.data[0])
                else:
                    persisted.append(rec_data)
            except Exception as e:
                logger.warning(f"Supabase remote insert failed: {e}")
                persisted.append(rec_data)
                
        self._save_cache_to_disk()
        return persisted

    def get_recommendations(self, user_id: str, status: Optional[str] = None, strategy: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recommendations for a user"""
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
            logger.warning(f"Failed to query remote table: {e}. Falling back to local cache.")

        results = [r for r in self._local_recommendations.values() if r.get('user_id') == user_id]
        if status:
            target_status = status.upper()
            results = [r for r in results if str(r.get('status', '')).upper() == target_status]
        if strategy:
            target_strat = str(strategy).lower()
            results = [r for r in results if str(r.get('strategy', '')).lower() == target_strat]

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
            logger.warning(f"Failed to fetch remote recommendation: {e}")

        return self._local_recommendations.get(recommendation_id)

    def update_recommendation(self, recommendation_id: str, update_data: Dict[str, Any]) -> bool:
        """Update recommendation status and outcome data"""
        data = dict(update_data)
        data['updated_at'] = datetime.now(timezone.utc).isoformat()

        if recommendation_id in self._local_recommendations:
            self._local_recommendations[recommendation_id].update(data)
            self._save_cache_to_disk()

        try:
            client = self._get_client()
            result = client.table('recommendations').update(data).eq('id', recommendation_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.warning(f"Failed to update remote recommendation: {e}")
            return recommendation_id in self._local_recommendations

    def health_check(self) -> Dict[str, Any]:
        """Check database connectivity and health"""
        try:
            client = self._get_client()
            result = client.table('interview_sessions').select('id').limit(1).execute()
            
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

    def store_question_skill_prediction(
        self,
        question_id: str,
        predicted_skills: List[Dict[str, Any]],
        confidence: float,
        model_version: str,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Persist ML-derived skill metadata for a question.
        Maintains strict separation between original question metadata and ML predictions.
        """
        record = {
            "id": str(uuid.uuid4()),
            "question_id": question_id,
            "predicted_skills": predicted_skills,
            "confidence": float(confidence),
            "model_version": model_version,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._local_question_skills[question_id] = record
        self._save_cache_to_disk()

        try:
            client = self._get_client()
            result = client.table("question_skill_predictions").insert(record).execute()
            if result.data:
                logger.info(f"Question skill prediction stored remotely for question {question_id}")
                return result.data[0]
        except Exception as e:
            logger.warning(f"Failed to store question skill prediction remotely: {e}. Stored in local fallback cache.")

        return record

    def get_question_skill_prediction(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve ML-derived skill metadata for a question."""
        try:
            client = self._get_client()
            result = client.table("question_skill_predictions").select("*").eq("question_id", question_id).execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            logger.debug(f"Failed to fetch question skill prediction remotely: {e}")

        return self._local_question_skills.get(question_id)
