"""
API blueprint — candidate skill intelligence and recommendations.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request

from app.security import require_auth, unauthorized_response
from app.schemas import UpdateRecommendationStatusRequest, success, error
from app.services.supabase_service import SupabaseService
from app.services.orchestrator.intelligence import SkillEvidenceAggregator
from app.services.orchestrator.recommendations import RecommendationEngine

logger = logging.getLogger(__name__)

intelligence_bp = Blueprint("intelligence", __name__)

_supabase = SupabaseService()
_aggregator = SkillEvidenceAggregator()
_recommendation_engine = RecommendationEngine()

# Backward-compatibility aliases for tests
supabase_service = _supabase
aggregator = _aggregator
recommendation_engine = _recommendation_engine


def _require_own_user(path_user_id: str):
    """Returns an error response tuple if the path user_id doesn't match the token."""
    if path_user_id != g.user_id:
        return unauthorized_response("You can only access your own data.")
    return None


# ─────────────────────────────────────────────────────────────────
# Skill profiles
# ─────────────────────────────────────────────────────────────────

@intelligence_bp.route("/skills/<user_id>", methods=["GET"])
@require_auth
def get_user_skills(user_id: str):
    """Return all longitudinal skill profiles for the authenticated user."""
    if (resp := _require_own_user(user_id)):
        return resp
    profiles = _supabase.get_user_skill_profiles(user_id)
    return jsonify(success({"user_id": user_id, "profiles": profiles})), 200


@intelligence_bp.route("/skills/<user_id>/<skill_name>", methods=["GET"])
@require_auth
def get_user_skill(user_id: str, skill_name: str):
    """Return a specific skill profile."""
    if (resp := _require_own_user(user_id)):
        return resp
    profile = _supabase.get_candidate_skill_profile(user_id, skill_name)
    if not profile:
        return jsonify(error(f"No profile found for skill '{skill_name}'", "SKILL_NOT_FOUND")), 404
    return jsonify(success({"user_id": user_id, "skill_name": skill_name, "profile": profile})), 200


# ─────────────────────────────────────────────────────────────────
# Recommendations
# ─────────────────────────────────────────────────────────────────

@intelligence_bp.route("/recommendations/<user_id>", methods=["GET"])
@require_auth
def get_recommendations(user_id: str):
    """Return persisted practice recommendations for the user."""
    if (resp := _require_own_user(user_id)):
        return resp
    status_filter = request.args.get("status")
    strategy_filter = request.args.get("strategy")
    limit = min(request.args.get("limit", 20, type=int), 100)
    recs = _supabase.get_recommendations(user_id, status=status_filter, strategy=strategy_filter, limit=limit)
    return jsonify(success({"user_id": user_id, "recommendations": recs, "total": len(recs)})), 200


@intelligence_bp.route("/recommendations/<user_id>/generate", methods=["POST"])
@require_auth
def generate_recommendations(user_id: str):
    """Generate and persist new evidence-based recommendations from skill profiles."""
    if (resp := _require_own_user(user_id)):
        return resp

    profiles = _supabase.get_user_skill_profiles(user_id)
    sessions = _supabase.get_user_sessions(user_id, limit=20)

    recs = _recommendation_engine.generate_recommendations(
        user_id=user_id,
        skill_profiles=profiles,
        sessions=sessions,
    )

    persisted = _supabase.create_recommendations(user_id, [r if isinstance(r, dict) else r.model_dump() for r in recs])
    logger.info("Generated %d recommendations for user %s", len(persisted), user_id)
    return jsonify(success({
        "user_id": user_id,
        "recommendations": persisted,
        "generated_count": len(persisted),
    }, "Recommendations generated")), 201


@intelligence_bp.route("/recommendations/<recommendation_id>/status", methods=["PATCH"])
@require_auth
def update_recommendation_status(recommendation_id: str):
    """Update the status of a recommendation the user owns."""
    data = request.get_json(silent=True) or {}
    try:
        req = UpdateRecommendationStatusRequest(**data)
    except Exception as exc:
        return jsonify(error(str(exc), "VALIDATION_ERROR")), 422

    rec = _supabase.get_recommendation(recommendation_id)
    if not rec:
        return jsonify(error("Recommendation not found", "NOT_FOUND")), 404
    if rec.get("user_id") != g.user_id:
        return unauthorized_response("You do not own this recommendation.")

    update = {"status": req.status}
    if req.outcome_score is not None:
        update["outcome_score"] = req.outcome_score
    if req.outcome_notes:
        update["outcome_notes"] = req.outcome_notes
    if req.status == "COMPLETED":
        update["completed_at"] = datetime.now(timezone.utc).isoformat()

    ok = _supabase.update_recommendation(recommendation_id, update)
    if not ok:
        return jsonify(error("Failed to update recommendation", "UPDATE_FAILED")), 500
    return jsonify(success({"recommendation_id": recommendation_id, "status": req.status}, "Status updated")), 200
