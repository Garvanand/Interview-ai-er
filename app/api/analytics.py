"""
API blueprint — longitudinal performance analytics.
"""
from __future__ import annotations

import logging

from flask import Blueprint, g, jsonify, request

from app.security import require_auth, unauthorized_response
from app.schemas import success, error
from app.analytics import LongitudinalAnalyticsService, AnalyticsFilter

logger = logging.getLogger(__name__)

analytics_bp = Blueprint("analytics", __name__)

_analytics = LongitudinalAnalyticsService()

# Backward-compatibility alias
analytics_service = _analytics


def _require_own_user(path_user_id: str):
    if path_user_id != g.user_id:
        return unauthorized_response("You can only access your own analytics.")
    return None


def _extract_filter() -> AnalyticsFilter:
    return AnalyticsFilter(
        start_date=request.args.get("start_date"),
        end_date=request.args.get("end_date"),
        interview_type=request.args.get("interview_type"),
        skill=request.args.get("skill"),
        difficulty=request.args.get("difficulty"),
        question_type=request.args.get("question_type"),
    )


@analytics_bp.route("/<user_id>", methods=["GET"])
@require_auth
def get_longitudinal_analytics(user_id: str):
    """
    Return complete longitudinal performance analytics for the user.
    Derived entirely from persisted database records.
    Supports query-parameter filtering: start_date, end_date, interview_type, skill, difficulty, question_type.
    """
    if (resp := _require_own_user(user_id)):
        return resp
    try:
        filters = _extract_filter()
        result = _analytics.get_longitudinal_analytics(user_id, filters)
        return jsonify(success(result.model_dump(mode="json"))), 200
    except Exception as exc:
        logger.error("Analytics computation error for user %s: %s", user_id, exc, exc_info=True)
        return jsonify(error(str(exc), "ANALYTICS_COMPUTATION_ERROR")), 500


@analytics_bp.route("/filter-options/<user_id>", methods=["GET"])
@require_auth
def get_filter_options(user_id: str):
    """Return the available filter values derived from the user's actual records."""
    if (resp := _require_own_user(user_id)):
        return resp
    try:
        options = _analytics.get_filter_options(user_id)
        return jsonify(success(options)), 200
    except Exception as exc:
        logger.error("Filter options error for user %s: %s", user_id, exc)
        return jsonify(error(str(exc), "FILTER_OPTIONS_ERROR")), 500


@analytics_bp.route("/trends/scores/<user_id>", methods=["GET"])
@require_auth
def get_score_trends(user_id: str):
    """Score trends with moving averages and trajectory slope."""
    if (resp := _require_own_user(user_id)):
        return resp
    try:
        result = _analytics.get_longitudinal_analytics(user_id, _extract_filter())
        return jsonify(success(result.score_trends.model_dump(mode="json"))), 200
    except Exception as exc:
        return jsonify(error(str(exc), "ANALYTICS_ERROR")), 500


@analytics_bp.route("/trends/skills/<user_id>", methods=["GET"])
@require_auth
def get_skill_trends(user_id: str):
    """Skill-level trajectories, confidence, and volatility."""
    if (resp := _require_own_user(user_id)):
        return resp
    try:
        result = _analytics.get_longitudinal_analytics(user_id, _extract_filter())
        return jsonify(success([s.model_dump(mode="json") for s in result.skill_trends])), 200
    except Exception as exc:
        return jsonify(error(str(exc), "ANALYTICS_ERROR")), 500


@analytics_bp.route("/consistency/<user_id>", methods=["GET"])
@require_auth
def get_consistency_analysis(user_id: str):
    """Dispersion, coefficient of variation, and stability index."""
    if (resp := _require_own_user(user_id)):
        return resp
    try:
        result = _analytics.get_longitudinal_analytics(user_id, _extract_filter())
        return jsonify(success(result.consistency.model_dump(mode="json"))), 200
    except Exception as exc:
        return jsonify(error(str(exc), "ANALYTICS_ERROR")), 500


@analytics_bp.route("/weaknesses/<user_id>", methods=["GET"])
@require_auth
def get_repeated_weaknesses(user_id: str):
    """Recurring weaknesses and blocker persistence classifications."""
    if (resp := _require_own_user(user_id)):
        return resp
    try:
        result = _analytics.get_longitudinal_analytics(user_id, _extract_filter())
        return jsonify(success([w.model_dump(mode="json") for w in result.repeated_weaknesses])), 200
    except Exception as exc:
        return jsonify(error(str(exc), "ANALYTICS_ERROR")), 500


@analytics_bp.route("/next-practice/<user_id>", methods=["GET"])
@require_auth
def get_next_practice_recommendations(user_id: str):
    """Evidence-based practice roadmap prioritized by impact."""
    if (resp := _require_own_user(user_id)):
        return resp
    try:
        result = _analytics.get_longitudinal_analytics(user_id, _extract_filter())
        return jsonify(success([p.model_dump(mode="json") for p in result.next_practice_recommendations])), 200
    except Exception as exc:
        return jsonify(error(str(exc), "ANALYTICS_ERROR")), 500
