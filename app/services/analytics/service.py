import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from app.services.supabase_service import SupabaseService
from .models import (
    AnalyticsFilter,
    LongitudinalAnalyticsResponse,
    ScoreTrendSummary,
    SkillTrendSummary,
    QuestionTypePerformance,
    DifficultyProgression,
    ConsistencyAnalysis,
    RepeatedWeakness,
    RecommendationImpact,
    RecentVsHistorical,
    CompletionBehavior,
    NextPracticeRecommendation
)
from .methodology import (
    parse_iso_datetime,
    calculate_score_trends,
    calculate_skill_trends,
    calculate_question_type_performance,
    calculate_difficulty_progression,
    calculate_consistency,
    calculate_repeated_weaknesses,
    calculate_recommendation_impact,
    calculate_recent_vs_historical,
    calculate_completion_behavior,
    generate_next_practice_recommendations
)

logger = logging.getLogger(__name__)

class LongitudinalAnalyticsService:
    """
    Orchestrates longitudinal performance analytics derived entirely from persisted records
    (sessions, questions, evaluations, skill_profiles, and recommendations).
    """

    def __init__(self, supabase_service: Optional[SupabaseService] = None):
        self.supabase = supabase_service or SupabaseService()

    def fetch_user_dataset(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieves all raw records associated with a user across sessions, questions,
        skill profiles, and recommendations.
        """
        # 1. Fetch sessions
        sessions = self.supabase.get_user_sessions(user_id, limit=200)

        # 2. Fetch questions for these sessions
        questions: List[Dict[str, Any]] = []
        if sessions:
            session_ids = [s['id'] for s in sessions if 'id' in s]
            try:
                client = self.supabase._get_client()
                # Batch query questions by session_ids
                if session_ids:
                    res = client.table('interview_questions').select('*, responses(*, evaluations(*))').in_('session_id', session_ids).order('created_at').execute()
                    if res.data:
                        for q in res.data:
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
            except Exception as e:
                logger.warning(f"Batch fetch of questions failed ({e}), falling back to iterative retrieval")
                for s_id in session_ids:
                    q_list = self.supabase.get_session_questions(s_id)
                    questions.extend(q_list)

        # 3. Fetch skill profiles
        skill_profiles = self.supabase.get_user_skill_profiles(user_id)

        # 4. Fetch recommendations
        recommendations = self.supabase.get_recommendations(user_id, limit=100)

        return {
            'sessions': sessions,
            'questions': questions,
            'skill_profiles': skill_profiles,
            'recommendations': recommendations
        }

    def apply_filters(
        self,
        sessions: List[Dict[str, Any]],
        questions: List[Dict[str, Any]],
        filters: AnalyticsFilter
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filters sessions and questions according to date range and attributes:
        interview_type, skill, difficulty, question_type.
        """
        start_dt = parse_iso_datetime(filters.start_date)
        end_dt = parse_iso_datetime(filters.end_date)

        # Filter questions
        filtered_questions: List[Dict[str, Any]] = []
        for q in questions:
            # Date filter
            q_dt = parse_iso_datetime(q.get('created_at'))
            if start_dt and q_dt and q_dt < start_dt:
                continue
            if end_dt and q_dt and q_dt > end_dt:
                continue

            # Interview type filter
            if filters.interview_type:
                target_it = filters.interview_type.lower()
                q_it = (q.get('interview_type') or '').lower()
                if target_it not in q_it:
                    continue

            # Skill filter
            if filters.skill:
                target_skill = filters.skill.lower()
                q_skill = (q.get('skill_focus') or q.get('interview_type') or '').lower()
                if target_skill not in q_skill:
                    continue

            # Difficulty filter
            if filters.difficulty:
                target_diff = filters.difficulty.lower()
                q_diff = (q.get('difficulty') or 'intermediate').lower()
                if target_diff != q_diff:
                    continue

            # Question Type / Modality filter
            if filters.question_type and filters.question_type != "all":
                target_qt = filters.question_type.lower()
                has_code = bool(q.get('code_text') or q.get('code_evaluation_score') or q.get('programming_language'))
                skill_text = f"{q.get('skill_focus', '')} {q.get('interview_type', '')}".lower()

                if target_qt == "coding" and not has_code:
                    continue
                elif target_qt == "system_design" and not any(k in skill_text for k in ["system", "design", "architecture"]):
                    continue
                elif target_qt == "algorithmic" and not any(k in skill_text for k in ["algorithm", "data struct", "leetcode"]):
                    continue
                elif target_qt in ("conceptual", "behavioral") and has_code:
                    continue

            filtered_questions.append(q)

        # Keep sessions that contain the filtered questions or match session-level filters
        valid_session_ids = {q.get('session_id') for q in filtered_questions if q.get('session_id')}

        filtered_sessions: List[Dict[str, Any]] = []
        for s in sessions:
            s_id = s.get('id')
            # Date filter
            s_dt = parse_iso_datetime(s.get('start_time'))
            if start_dt and s_dt and s_dt < start_dt:
                continue
            if end_dt and s_dt and s_dt > end_dt:
                continue

            # Interview type filter
            if filters.interview_type:
                target_it = filters.interview_type.lower()
                s_it = (s.get('interview_type') or '').lower()
                if target_it not in s_it:
                    continue

            # If specific question-level filters (skill, difficulty, question_type) are active,
            # ensure session has at least one matching question
            has_question_filters = bool(filters.skill or filters.difficulty or (filters.question_type and filters.question_type != "all"))
            if has_question_filters and s_id not in valid_session_ids:
                continue

            filtered_sessions.append(s)

        return filtered_sessions, filtered_questions

    def get_longitudinal_analytics(
        self,
        user_id: str,
        filters: Optional[AnalyticsFilter] = None
    ) -> LongitudinalAnalyticsResponse:
        """
        Executes full longitudinal performance analytics for a candidate.
        All metrics are strictly calculated from persisted evidence.
        """
        filters = filters or AnalyticsFilter()
        raw_data = self.fetch_user_dataset(user_id)

        all_sessions = raw_data['sessions']
        all_questions = raw_data['questions']
        raw_profiles = raw_data['skill_profiles']
        raw_recommendations = raw_data['recommendations']

        # Apply user filters
        sessions, questions = self.apply_filters(all_sessions, all_questions, filters)

        # Map questions by session_id
        questions_by_session: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for q in questions:
            s_id = q.get('session_id')
            if s_id:
                questions_by_session[s_id].append(q)

        # 1. Interview score trends
        score_trends = calculate_score_trends(sessions, questions_by_session)

        # 2. Skill trends
        skill_trends = calculate_skill_trends(questions, raw_profiles)

        # 3. Question-type performance
        question_type_perf = calculate_question_type_performance(questions)

        # 4. Difficulty progression
        difficulty_progression = calculate_difficulty_progression(questions)

        # 5. Consistency
        question_scores = [
            float(q.get('evaluation_score') or q.get('code_evaluation_score'))
            for q in questions
            if (q.get('evaluation_score') is not None or q.get('code_evaluation_score') is not None)
        ]
        consistency = calculate_consistency(question_scores)

        # 6. Repeated weaknesses
        repeated_weaknesses = calculate_repeated_weaknesses(questions, len(sessions))

        # 7. Improvement after recommendations
        recommendation_impact = calculate_recommendation_impact(raw_recommendations, all_questions)

        # 8. Recent vs historical performance
        recent_vs_hist = calculate_recent_vs_historical(sessions, questions)

        # 9. Interview completion behavior
        completion_behavior = calculate_completion_behavior(sessions, questions)

        # 10. Next-practice recommendations (Actionability matrix)
        next_practice = generate_next_practice_recommendations(
            skill_trends=skill_trends,
            repeated_weaknesses=repeated_weaknesses,
            difficulty_progression=difficulty_progression,
            consistency=consistency
        )

        # 11. Session-level evidence audit log (last 10 sessions with question details)
        session_evidence = []
        for s in sessions[-10:]:
            s_id = s.get('id')
            s_qs = questions_by_session.get(s_id, [])
            session_evidence.append({
                'session_id': s_id,
                'interview_type': s.get('interview_type'),
                'start_time': s.get('start_time'),
                'score': s.get('score'),
                'status': s.get('status'),
                'questions': [
                    {
                        'question_id': q.get('id'),
                        'question_text': q.get('question_text'),
                        'difficulty': q.get('difficulty'),
                        'skill_focus': q.get('skill_focus'),
                        'score': q.get('evaluation_score') or q.get('code_evaluation_score'),
                        'feedback': q.get('evaluation_feedback') or (q.get('code_evaluation_details') or {}).get('feedback', ''),
                        'is_code': bool(q.get('code_text') or q.get('code_evaluation_score'))
                    }
                    for q in s_qs
                ]
            })

        return LongitudinalAnalyticsResponse(
            user_id=user_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            filters_applied=filters,
            score_trends=score_trends,
            skill_trends=skill_trends,
            question_type_performance=question_type_perf,
            difficulty_progression=difficulty_progression,
            consistency=consistency,
            repeated_weaknesses=repeated_weaknesses,
            recommendation_impact=recommendation_impact,
            recent_vs_historical=recent_vs_hist,
            completion_behavior=completion_behavior,
            next_practice_recommendations=next_practice,
            session_evidence=session_evidence
        )

    def get_filter_options(self, user_id: str) -> Dict[str, Any]:
        """
        Returns the real available filter values found in the user's persisted records.
        """
        raw_data = self.fetch_user_dataset(user_id)
        sessions = raw_data['sessions']
        questions = raw_data['questions']

        interview_types = set()
        skills = set()
        difficulties = set()
        dates = []

        for s in sessions:
            it = s.get('interview_type')
            if it:
                interview_types.add(it)
            st = s.get('start_time')
            if st:
                dates.append(st)

        for q in questions:
            sk = q.get('skill_focus')
            if sk:
                skills.add(sk)
            diff = q.get('difficulty')
            if diff:
                difficulties.add(diff.lower())
            ct = q.get('created_at')
            if ct:
                dates.append(ct)

        for p in raw_data['skill_profiles']:
            p_sk = p.get('skill_name')
            if p_sk:
                skills.add(p_sk)

        dates_sorted = sorted([d for d in dates if d])

        return {
            'interview_types': sorted(list(interview_types)),
            'skills': sorted(list(skills)),
            'difficulties': ["beginner", "intermediate", "advanced"],
            'question_types': ["all", "coding", "system_design", "algorithmic", "conceptual_behavioral"],
            'earliest_date': dates_sorted[0] if dates_sorted else None,
            'latest_date': dates_sorted[-1] if dates_sorted else None,
            'total_sessions_count': len(sessions),
            'total_questions_count': len(questions)
        }
