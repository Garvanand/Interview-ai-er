"""
API blueprint — interview session, evaluation, and code execution routes.

This file is the HTTP transport layer only.
It validates requests, delegates to services, and serializes responses.
No business logic lives here.
"""
from __future__ import annotations

import logging

from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError

from app.security import (
    require_auth,
    verify_session_ownership,
    unauthorized_response,
    not_found_response,
    SecurityService,
)
from app.schemas import (
    StartSessionRequest,
    SubmitAnswerRequest,
    SubmitCodeRequest,
    FollowUpRequest,
    SecurityCheckRequest,
    success,
    error,
)
from app.services.supabase_service import SupabaseService
from app.ai import AssessmentEngine, GeminiProvider
from app.services.orchestrator import InterviewOrchestrator
from app.infrastructure import CodeSandbox

logger = logging.getLogger(__name__)

interview_bp = Blueprint("interview", __name__)

# Service singletons — initialized once per worker process
_supabase = SupabaseService()
_ai_engine = AssessmentEngine(GeminiProvider())
_security = SecurityService()
_orchestrator = InterviewOrchestrator(_supabase, _ai_engine)
_sandbox = CodeSandbox(timeout_seconds=5)

# Keep these names for backward compatibility with tests
supabase_service = _supabase
ai_engine = _ai_engine
security_service = _security
orchestrator = _orchestrator
sandbox = _sandbox


def _parse_json(schema_class):
    """Parse and validate request JSON against a Pydantic schema.
    Returns (instance, None) or (None, error_response_tuple)."""
    data = request.get_json(silent=True)
    if not data:
        return None, (jsonify(error("Request body is missing or not JSON", "NO_BODY")), 400)
    try:
        return schema_class(**data), None
    except ValidationError as exc:
        messages = "; ".join(f"{e['loc'][0]}: {e['msg']}" for e in exc.errors())
        return None, (jsonify(error(messages, "VALIDATION_ERROR")), 422)


# ─────────────────────────────────────────────────────────────────
# Session management
# ─────────────────────────────────────────────────────────────────

@interview_bp.route("/start_session", methods=["POST"])
@require_auth
def start_session():
    """Create a new interview session and initialize the orchestrator."""
    req, err = _parse_json(StartSessionRequest)
    if err:
        return err

    user_id = g.user_id

    # Normalize legacy type names
    type_aliases = {
        "Technical": "Software Engineer",
        "Coding": "Software Engineer",
        "System Design": "Software Engineer",
        "Behavioral": "Software Engineer",
    }
    interview_type = type_aliases.get(req.interview_type, req.interview_type)

    result = _supabase.create_session(user_id, interview_type)
    if not result.get("success"):
        logger.error("Session creation failed: %s", result.get("error"))
        return jsonify(error("Failed to start session", "SESSION_CREATION_FAILED")), 500

    session_id = result["session_id"]
    state = _orchestrator.initialize_session(
        session_id=session_id,
        user_id=user_id,
        target_role=interview_type,
        interview_type=interview_type,
    )
    _supabase.log_event(session_id, "session_started", {"user_id": user_id, "interview_type": interview_type})

    logger.info("Session started: %s (user=%s, type=%s)", session_id, user_id, interview_type)
    return jsonify(success({
        "session_id": session_id,
        "user_id": user_id,
        "interview_type": interview_type,
        "start_time": result["data"]["start_time"],
        "phase": state.phase.value,
        "difficulty": state.difficulty.value,
        "skills": list(state.skills_distribution.keys()),
    }, "Session started successfully")), 201


@interview_bp.route("/get_question", methods=["GET"])
@require_auth
def get_question():
    """Return the next question from the orchestrator for an active session."""
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify(error("session_id is required", "MISSING_SESSION_ID")), 400

    if not verify_session_ownership(session_id, g.user_id):
        return unauthorized_response("You do not have access to this session.")

    session = _supabase.get_session(session_id)
    if not session:
        return not_found_response("Session not found.")
    if session.get("status") != "active":
        return jsonify(error("Session is not active", "SESSION_INACTIVE")), 400

    result = _orchestrator.get_next_question(session_id)
    return jsonify(success(result, "Question retrieved successfully")), 200


@interview_bp.route("/submit_answer", methods=["POST"])
@require_auth
def submit_answer():
    """Submit a text answer for evaluation."""
    req, err = _parse_json(SubmitAnswerRequest)
    if err:
        return err

    if not verify_session_ownership(req.session_id, g.user_id):
        return unauthorized_response("You do not have access to this session.")

    session = _supabase.get_session(req.session_id)
    if not session or session.get("status") != "active":
        return jsonify(error("Session not found or not active", "SESSION_INVALID")), 404

    if len(req.answer_text) < 10:
        return jsonify(error("Answer must be at least 10 characters", "ANSWER_TOO_SHORT")), 400

    result = _orchestrator.record_and_evaluate_answer(
        session_id=req.session_id,
        question_id=req.question_id,
        answer_text=req.answer_text,
        is_code=False,
    )
    return jsonify(success({
        "question_id": req.question_id,
        "evaluation": result["evaluation"],
        "session_score": result["session_score"],
        "current_difficulty": result["current_difficulty"],
        "difficulty_adjusted": result["difficulty_adjusted"],
        "current_phase": result["current_phase"],
        "is_last_question": result["is_last_question"],
        "skills_overview": result["skills_overview"],
    }, "Answer submitted successfully")), 200


@interview_bp.route("/submit_code", methods=["POST"])
@require_auth
def submit_code():
    """Submit code for AI evaluation and persist the submission."""
    req, err = _parse_json(SubmitCodeRequest)
    if err:
        return err

    if not verify_session_ownership(req.session_id, g.user_id):
        return unauthorized_response("You do not have access to this session.")

    session = _supabase.get_session(req.session_id)
    if not session or session.get("status") != "active":
        return jsonify(error("Session not active", "SESSION_INACTIVE")), 400

    result = _orchestrator.record_and_evaluate_answer(
        session_id=req.session_id,
        question_id=req.question_id,
        answer_text=req.code,
        is_code=True,
        language=req.language,
    )
    return jsonify(success({
        "evaluation": result["evaluation"],
        "session_score": result["session_score"],
        "current_difficulty": result["current_difficulty"],
        "current_phase": result["current_phase"],
        "is_last_question": result["is_last_question"],
    }, "Code submitted successfully")), 200


@interview_bp.route("/run_code", methods=["POST"])
@require_auth
def run_code():
    """Execute code in the sandbox without creating a submission record."""
    data = request.get_json(silent=True) or {}
    code = data.get("code", "").strip()
    language = data.get("language", "").strip()
    if not code or not language:
        return jsonify(error("code and language are required", "MISSING_FIELDS")), 400

    result = _sandbox.execute(code, language)
    return jsonify(success(result, "Code executed")), 200


# ─────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────

@interview_bp.route("/session/<session_id>", methods=["GET"])
@require_auth
def get_session_details(session_id: str):
    """Return aggregated session statistics, questions, events, and anomalies."""
    if not verify_session_ownership(session_id, g.user_id):
        return unauthorized_response("You do not have access to this session.")
    stats = _supabase.get_session_statistics(session_id)
    return jsonify(success(stats, "Session details retrieved")), 200


@interview_bp.route("/session/<session_id>/state", methods=["GET"])
@require_auth
def get_session_orchestrator_state(session_id: str):
    """Return backend-authoritative orchestrator state for the session."""
    if not verify_session_ownership(session_id, g.user_id):
        return unauthorized_response("You do not have access to this session.")
    state = _orchestrator.get_session_state(session_id)
    return jsonify(success(state, "Session state retrieved")), 200


@interview_bp.route("/end_session/<session_id>", methods=["POST"])
@require_auth
def end_session(session_id: str):
    """Finalize a session, trigger synthesis, and mark it as completed."""
    if not verify_session_ownership(session_id, g.user_id):
        return unauthorized_response("You do not have access to this session.")

    session = _supabase.get_session(session_id)
    if not session:
        return not_found_response("Session not found.")
    if session.get("status") == "completed":
        return jsonify(error("Session is already completed", "SESSION_ALREADY_COMPLETED")), 400

    final = _orchestrator.finalize_interview(session_id)
    return jsonify(success(final, "Session ended successfully")), 200


@interview_bp.route("/user/<user_id>/sessions", methods=["GET"])
@require_auth
def get_user_sessions(user_id: str):
    """List recent interview sessions for the authenticated user."""
    if user_id != g.user_id:
        return unauthorized_response("You can only access your own sessions.")
    limit = min(max(request.args.get("limit", 10, type=int), 1), 50)
    sessions = _supabase.get_user_sessions(user_id, limit)
    return jsonify(success(
        {"user_id": user_id, "sessions": sessions, "total_count": len(sessions)},
        "Sessions retrieved",
    )), 200


# ─────────────────────────────────────────────────────────────────
# Follow-up and practice
# ─────────────────────────────────────────────────────────────────

@interview_bp.route("/follow_up_question", methods=["POST"])
@require_auth
def get_follow_up_question():
    """Generate a targeted follow-up question for a given Q&A pair."""
    req, err = _parse_json(FollowUpRequest)
    if err:
        return err
    follow_up_data = _ai_engine.generate_follow_up_question(req.question, req.answer, {})
    follow_up = follow_up_data.get("question_text", str(follow_up_data))
    return jsonify(success({
        "follow_up_question": follow_up,
        "context": {"original_question": req.question, "interview_type": req.interview_type},
    }, "Follow-up question generated")), 200


@interview_bp.route("/practice/coding", methods=["POST"])
@require_auth
def practice_coding():
    """Generate a coding practice question outside of a formal session."""
    data = request.get_json(silent=True) or {}
    interview_type = data.get("interview_type", "").strip()
    if not interview_type:
        return jsonify(error("interview_type is required", "MISSING_INTERVIEW_TYPE")), 400
    difficulty = data.get("difficulty", "intermediate")
    topic = data.get("topic", "coding")
    question_data = _ai_engine.generate_question("coding", difficulty, topic=topic)
    return jsonify(success({
        "question": question_data.get("question_text", str(question_data)),
        "interview_type": interview_type,
        "difficulty": difficulty,
        "topic": topic,
    }, "Practice question generated")), 200


# ─────────────────────────────────────────────────────────────────
# Session integrity
# ─────────────────────────────────────────────────────────────────

@interview_bp.route("/security/check", methods=["POST"])
@require_auth
def security_check():
    """Process a batch of browser events and return a session integrity report."""
    req, err = _parse_json(SecurityCheckRequest)
    if err:
        return err

    if not verify_session_ownership(req.session_id, g.user_id):
        return unauthorized_response("You do not have access to this session.")

    report = _security.process_raw_events(req.session_id, req.events)
    if report.review_recommended:
        _supabase.log_anomaly(
            req.session_id,
            "session_integrity_flag",
            "HIGH" if report.aggregation_score > 0.8 else "MEDIUM",
            {
                "aggregation_score": report.aggregation_score,
                "signals": [sig.model_dump() for sig in report.signals],
                "confidence": report.confidence_in_assessment,
            },
        )
    return jsonify(success({
        "review_recommended": report.review_recommended,
        "aggregation_score": report.aggregation_score,
        "signals": [sig.model_dump() for sig in report.signals],
        "summary": report.summary,
        "confidence": report.confidence_in_assessment,
    }, "Integrity check completed")), 200


@interview_bp.route("/security/report/<session_id>", methods=["GET"])
@require_auth
def get_security_report(session_id: str):
    """Return persisted integrity events for a session."""
    if not verify_session_ownership(session_id, g.user_id):
        return unauthorized_response("You do not have access to this session.")
    # Delegated to the logging blueprint via shared service
    return jsonify(error("Use /api/anomalies/<session_id>", "USE_ANOMALIES_ENDPOINT")), 301
