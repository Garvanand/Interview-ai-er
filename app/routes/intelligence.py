from flask import Blueprint, request, jsonify, current_app, g
from app.services.supabase_service import SupabaseService
from app.services.orchestrator.intelligence import (
    CandidateSkillProfile,
    SkillEvidenceAggregator,
    SkillEvidence
)
from app.services.orchestrator.recommendations import (
    RecommendationEngine,
    Recommendation,
    RecommendationStatus,
    RecommendationStrategy
)
from app.auth import require_auth
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

intelligence_bp = Blueprint('intelligence', __name__)
supabase_service = SupabaseService()
aggregator = SkillEvidenceAggregator()
recommendation_engine = RecommendationEngine()


# ============================================================================
# Longitudinal Candidate Skill Intelligence Endpoints
# ============================================================================

@intelligence_bp.route('/skills/<user_id>', methods=['GET'])
@require_auth
def get_user_skills(user_id):
    """Retrieve all longitudinal skill profiles for a user."""
    try:
        if user_id != g.user_id:
            return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
            
        profiles = supabase_service.get_user_skill_profiles(user_id)
        return jsonify({
            'success': True,
            'user_id': user_id,
            'profiles': profiles
        }), 200
    except Exception as e:
        logger.error(f"Failed to retrieve skill profiles: {str(e)}")
        return jsonify({
            'error': True,
            'message': str(e),
            'code': 'INTERNAL_ERROR'
        }), 500

@intelligence_bp.route('/skills/<user_id>/<skill_name>', methods=['GET'])
@require_auth
def get_user_skill(user_id, skill_name):
    """Retrieve a specific longitudinal skill profile for a user."""
    try:
        if user_id != g.user_id:
            return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
            
        profile = supabase_service.get_candidate_skill_profile(user_id, skill_name)
        if profile:
            return jsonify({
                'success': True,
                'user_id': user_id,
                'skill_name': skill_name,
                'profile': profile
            }), 200
        else:
            return jsonify({
                'success': True,
                'user_id': user_id,
                'skill_name': skill_name,
                'profile': {
                    'estimated_proficiency': 0.0,
                    'confidence': 'insufficient evidence',
                    'evidence_count': 0,
                    'recent_performance': 0.0,
                    'historical_performance': 0.0,
                    'improvement_trend': 'neutral'
                }
            }), 200
    except Exception as e:
        logger.error(f"Failed to retrieve skill profile: {str(e)}")
        return jsonify({
            'error': True,
            'message': str(e),
            'code': 'INTERNAL_ERROR'
        }), 500

@intelligence_bp.route('/skills/<user_id>/evaluate', methods=['POST'])
@require_auth
def process_evaluation_evidence(user_id):
    """
    Process new evidence from an evaluation and update the candidate's longitudinal skill profile.
    """
    try:
        if user_id != g.user_id:
            return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
            
        data = request.json or {}
        skill_name = data.get('skill_name')
        session_id = data.get('session_id')
        question_id = data.get('question_id')
        score = data.get('score')
        
        if not all([skill_name, session_id, question_id, score is not None]):
            return jsonify({'error': True, 'message': 'Missing required fields'}), 400
            
        evidence = SkillEvidence(
            session_id=session_id,
            question_id=question_id,
            score=float(score)
        )
        
        # Load existing profile
        existing_profile_data = supabase_service.get_candidate_skill_profile(user_id, skill_name)
        if existing_profile_data:
            history = [SkillEvidence(**e) for e in existing_profile_data.get('evidence_history', [])]
            profile = CandidateSkillProfile(
                user_id=user_id,
                skill_name=skill_name,
                estimated_proficiency=existing_profile_data.get('estimated_proficiency', 0.0),
                confidence=existing_profile_data.get('confidence', 'insufficient evidence'),
                evidence_count=existing_profile_data.get('evidence_count', 0),
                recent_performance=existing_profile_data.get('recent_performance', 0.0),
                historical_performance=existing_profile_data.get('historical_performance', 0.0),
                improvement_trend=existing_profile_data.get('improvement_trend', 'neutral'),
                last_evaluated_timestamp=existing_profile_data.get('last_evaluated_timestamp'),
                evidence_history=history
            )
        else:
            profile = CandidateSkillProfile(user_id=user_id, skill_name=skill_name)
            
        # Process new evidence
        updated_profile = aggregator.process_evidence(profile, evidence)
        
        # Save to database
        profile_dict = updated_profile.model_dump()
        success = supabase_service.update_candidate_skill_profile(user_id, skill_name, profile_dict)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully',
                'profile': profile_dict
            }), 200
        else:
            return jsonify({
                'error': True,
                'message': 'Failed to save profile update',
                'code': 'DB_ERROR'
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to process evaluation evidence: {str(e)}")
        return jsonify({
            'error': True,
            'message': str(e),
            'code': 'INTERNAL_ERROR'
        }), 500


# ============================================================================
# Personalized Recommendation Engine Endpoints
# ============================================================================

@intelligence_bp.route('/recommendations/<user_id>', methods=['GET'])
@require_auth
def get_user_recommendations(user_id):
    """
    Retrieve persisted recommendations for a candidate with optional filtering.
    Query parameters:
      - status: PENDING, ACCEPTED, COMPLETED, DISMISSED
      - strategy: next_interview, practice_session, skill_reinforcement, weak_signal_validation, review_prior_mistakes
      - limit: int (default 20)
    """
    try:
        if user_id != g.user_id:
            return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
            
        status = request.args.get('status')
        strategy = request.args.get('strategy')
        limit = request.args.get('limit', 20, type=int)

        recommendations = supabase_service.get_recommendations(
            user_id=user_id,
            status=status,
            strategy=strategy,
            limit=limit
        )

        return jsonify({
            'success': True,
            'user_id': user_id,
            'count': len(recommendations),
            'recommendations': recommendations
        }), 200
    except Exception as e:
        logger.error(f"Failed to get recommendations for user {user_id}: {e}")
        return jsonify({
            'error': True,
            'message': str(e),
            'code': 'INTERNAL_ERROR'
        }), 500


@intelligence_bp.route('/recommendations/<user_id>/generate', methods=['POST'])
@require_auth
def generate_recommendations(user_id):
    """
    Generate evidence-backed recommendations for a user based on their longitudinal
    skill profiles and recent interview interaction history.
    """
    try:
        if user_id != g.user_id:
            return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
            
        data = request.get_json(silent=True) or {}
        session_id = data.get('session_id')

        # 1. Fetch longitudinal skill profiles
        raw_profiles = supabase_service.get_user_skill_profiles(user_id)
        skill_profiles: list[CandidateSkillProfile] = []
        for p in raw_profiles:
            try:
                history = [SkillEvidence(**e) for e in p.get('evidence_history', [])]
                skill_profiles.append(CandidateSkillProfile(
                    user_id=user_id,
                    skill_name=p.get('skill_name', ''),
                    estimated_proficiency=p.get('estimated_proficiency', 0.0),
                    confidence=p.get('confidence', 'insufficient evidence'),
                    evidence_count=p.get('evidence_count', 0),
                    recent_performance=p.get('recent_performance', 0.0),
                    historical_performance=p.get('historical_performance', 0.0),
                    improvement_trend=p.get('improvement_trend', 'neutral'),
                    last_evaluated_timestamp=p.get('last_evaluated_timestamp'),
                    evidence_history=history
                ))
            except Exception as parse_err:
                logger.warning(f"Error parsing skill profile: {parse_err}")

        # 2. Fetch session questions if session_id provided or latest session
        session_questions = []
        if session_id:
            session_questions = supabase_service.get_session_questions(session_id)
        else:
            recent_sessions = supabase_service.get_user_sessions(user_id, limit=1)
            if recent_sessions:
                latest_session_id = recent_sessions[0].get('id')
                if latest_session_id:
                    session_id = latest_session_id
                    session_questions = supabase_service.get_session_questions(latest_session_id)

        # 3. Generate recommendations via RecommendationEngine
        recommendations = recommendation_engine.generate_recommendations(
            user_id=user_id,
            skill_profiles=skill_profiles,
            session_questions=session_questions,
            session_id=session_id
        )

        # 4. Persist to database
        recs_dict = [r.model_dump(mode='json') for r in recommendations]
        persisted = supabase_service.create_recommendations(user_id, recs_dict)

        return jsonify({
            'success': True,
            'user_id': user_id,
            'count': len(persisted),
            'recommendations': persisted
        }), 201

    except Exception as e:
        logger.error(f"Failed to generate recommendations for user {user_id}: {e}")
        return jsonify({
            'error': True,
            'message': str(e),
            'code': 'INTERNAL_ERROR'
        }), 500


@intelligence_bp.route('/recommendations/<recommendation_id>/status', methods=['PATCH'])
@require_auth
def update_recommendation_status(recommendation_id):
    """
    Update the status of a recommendation (e.g. ACCEPTED, COMPLETED, DISMISSED).
    """
    try:
        data = request.get_json() or {}
        new_status = data.get('status')
        if not new_status:
            return jsonify({'error': True, 'message': 'Status is required'}), 400

        normalized_status = new_status.upper()
        valid_statuses = [s.value for s in RecommendationStatus]
        if normalized_status not in valid_statuses:
            return jsonify({
                'error': True,
                'message': f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }), 400

        rec_data = supabase_service.get_recommendation(recommendation_id)
        if not rec_data or rec_data.get('user_id') != g.user_id:
            return jsonify({'error': True, 'message': 'Recommendation not found or unauthorized'}), 404

        update_payload = {'status': normalized_status}
        if normalized_status == RecommendationStatus.COMPLETED.value:
            update_payload['completed_at'] = datetime.now(timezone.utc).isoformat()

        success = supabase_service.update_recommendation(recommendation_id, update_payload)
        if not success:
            return jsonify({'error': True, 'message': 'Recommendation update failed'}), 500

        updated_rec = supabase_service.get_recommendation(recommendation_id)
        return jsonify({
            'success': True,
            'message': f"Recommendation status updated to {normalized_status}",
            'recommendation': updated_rec
        }), 200

    except Exception as e:
        logger.error(f"Failed to update recommendation status: {e}")
        return jsonify({
            'error': True,
            'message': str(e),
            'code': 'INTERNAL_ERROR'
        }), 500


@intelligence_bp.route('/recommendations/<recommendation_id>/evaluate_outcome', methods=['POST'])
@require_auth
def evaluate_recommendation_outcome(recommendation_id):
    """
    Evaluate whether the candidate followed the recommendation and whether subsequent
    performance improved. Calculates delta from baseline proficiency and sets outcome status.
    """
    try:
        data = request.get_json(silent=True) or {}
        rec_data = supabase_service.get_recommendation(recommendation_id)
        if not rec_data or rec_data.get('user_id') != g.user_id:
            return jsonify({'error': True, 'message': 'Recommendation not found or unauthorized'}), 404

        user_id = rec_data.get('user_id')
        target_skill = rec_data.get('target_skill')
        baseline_prof = float(rec_data.get('baseline_proficiency', 0.0))

        # Determine current proficiency: either provided in request or fetched from DB
        current_prof = data.get('current_proficiency')
        if current_prof is None:
            skill_profile = supabase_service.get_candidate_skill_profile(user_id, target_skill)
            if skill_profile:
                current_prof = float(skill_profile.get('estimated_proficiency', baseline_prof))
            else:
                current_prof = baseline_prof
        else:
            current_prof = float(current_prof)

        # Parse recommendation into domain model
        rec_model = Recommendation(**rec_data)

        # Evaluate outcome
        evaluated_rec = recommendation_engine.evaluate_outcome(rec_model, current_prof)
        evaluated_dict = evaluated_rec.model_dump(mode='json')

        # Update in database
        supabase_service.update_recommendation(recommendation_id, evaluated_dict)

        return jsonify({
            'success': True,
            'message': 'Recommendation outcome evaluated successfully',
            'outcome': {
                'recommendation_id': recommendation_id,
                'target_skill': target_skill,
                'baseline_proficiency': baseline_prof,
                'post_outcome_proficiency': current_prof,
                'outcome_delta': evaluated_rec.outcome_delta,
                'outcome_assessment': evaluated_rec.outcome_assessment,
                'status': evaluated_rec.status.value,
                'completed_at': evaluated_rec.completed_at
            },
            'recommendation': evaluated_dict
        }), 200

    except Exception as e:
        logger.error(f"Failed to evaluate recommendation outcome: {e}")
        return jsonify({
            'error': True,
            'message': str(e),
            'code': 'INTERNAL_ERROR'
        }), 500
