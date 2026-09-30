import logging
from flask import Blueprint, request, jsonify, g
from app.auth import require_auth
from app.services.analytics import (
    LongitudinalAnalyticsService,
    AnalyticsFilter
)
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__)
analytics_service = LongitudinalAnalyticsService()

def _extract_filter_from_query() -> AnalyticsFilter:
    """Helper to extract filter parameters from request query string."""
    return AnalyticsFilter(
        start_date=request.args.get('start_date'),
        end_date=request.args.get('end_date'),
        interview_type=request.args.get('interview_type'),
        skill=request.args.get('skill'),
        difficulty=request.args.get('difficulty'),
        question_type=request.args.get('question_type')
    )

@analytics_bp.route('/<user_id>', methods=['GET'])
@require_auth
def get_user_longitudinal_analytics(user_id: str):
    if user_id != g.user_id:
        return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
    """
    Primary endpoint returning complete longitudinal performance analytics
    based entirely on persisted database evidence.
    Supports query parameter filtering by date range, interview type, skill, difficulty, and question type.
    """
    try:
        filters = _extract_filter_from_query()
        response = analytics_service.get_longitudinal_analytics(user_id, filters)
        return jsonify({
            'success': True,
            'data': response.model_dump(mode='json')
        }), 200
    except Exception as e:
        logger.error(f"Error computing longitudinal analytics for user {user_id}: {e}", exc_info=True)
        return jsonify({
            'error': True,
            'message': str(e),
            'code': 'ANALYTICS_COMPUTATION_ERROR'
        }), 500

@analytics_bp.route('/filter-options/<user_id>', methods=['GET'])
@require_auth
def get_filter_options(user_id: str):
    if user_id != g.user_id:
        return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
    """
    Returns available filter choices present in candidate's real stored records.
    """
    try:
        options = analytics_service.get_filter_options(user_id)
        return jsonify({
            'success': True,
            'data': options
        }), 200
    except Exception as e:
        logger.error(f"Error retrieving filter options for user {user_id}: {e}")
        return jsonify({
            'error': True,
            'message': str(e),
            'code': 'FILTER_OPTIONS_ERROR'
        }), 500

@analytics_bp.route('/trends/scores/<user_id>', methods=['GET'])
@require_auth
def get_score_trends(user_id: str):
    """Returns focused score trends with moving averages and trajectory slope."""
    if user_id != g.user_id:
        return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
    try:
        filters = _extract_filter_from_query()
        res = analytics_service.get_longitudinal_analytics(user_id, filters)
        return jsonify({
            'success': True,
            'data': res.score_trends.model_dump(mode='json')
        }), 200
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@analytics_bp.route('/trends/skills/<user_id>', methods=['GET'])
@require_auth
def get_skill_trends(user_id: str):
    """Returns longitudinal skill trajectories, confidence, and volatility."""
    if user_id != g.user_id:
        return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
    try:
        filters = _extract_filter_from_query()
        res = analytics_service.get_longitudinal_analytics(user_id, filters)
        return jsonify({
            'success': True,
            'data': [s.model_dump(mode='json') for s in res.skill_trends]
        }), 200
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@analytics_bp.route('/consistency/<user_id>', methods=['GET'])
@require_auth
def get_consistency_analysis(user_id: str):
    """Returns dispersion, coefficient of variation, and stability index."""
    if user_id != g.user_id:
        return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
    try:
        filters = _extract_filter_from_query()
        res = analytics_service.get_longitudinal_analytics(user_id, filters)
        return jsonify({
            'success': True,
            'data': res.consistency.model_dump(mode='json')
        }), 200
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@analytics_bp.route('/weaknesses/<user_id>', methods=['GET'])
@require_auth
def get_repeated_weaknesses(user_id: str):
    """Returns recurring weaknesses and blocker persistence classifications."""
    if user_id != g.user_id:
        return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
    try:
        filters = _extract_filter_from_query()
        res = analytics_service.get_longitudinal_analytics(user_id, filters)
        return jsonify({
            'success': True,
            'data': [w.model_dump(mode='json') for w in res.repeated_weaknesses]
        }), 200
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@analytics_bp.route('/next-practice/<user_id>', methods=['GET'])
@require_auth
def get_next_practice_recommendations(user_id: str):
    """Returns prioritized evidence-based practice roadmap."""
    if user_id != g.user_id:
        return jsonify({'error': True, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 403
    try:
        filters = _extract_filter_from_query()
        res = analytics_service.get_longitudinal_analytics(user_id, filters)
        return jsonify({
            'success': True,
            'data': [p.model_dump(mode='json') for p in res.next_practice_recommendations]
        }), 200
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500
