"""
Repository layer — all Supabase data access.

Thin wrappers around the Supabase client that translate raw dicts to/from
typed domain dictionaries. No business logic here.

Why a repository layer instead of direct service access?
- Single place to change if the DB client or schema changes.
- Routes and services stay clean — they request data, not construct queries.
- Testable in isolation by swapping the client mock.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from supabase import Client, create_client
from flask import current_app

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Lazy-initialized, singleton Supabase client for a Flask request context.
    Call `get()` to obtain the client within a request.
    """
    _client: Optional[Client] = None

    @classmethod
    def get(cls) -> Client:
        if cls._client is None:
            url = current_app.config["SUPABASE_URL"]
            key = current_app.config["SUPABASE_KEY"]
            cls._client = create_client(url, key)
        return cls._client

    @classmethod
    def reset(cls) -> None:
        """Force client re-initialisation (useful in tests)."""
        cls._client = None


# ─────────────────────────────────────────────────────────────────
# Session repository
# ─────────────────────────────────────────────────────────────────

class SessionRepository:
    def create(self, user_id: str, interview_type: str) -> Dict[str, Any]:
        client = SupabaseClient.get()
        data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "interview_type": interview_type,
            "start_time": _now(),
            "score": 0.0,
            "status": "INITIALIZING",
        }
        result = client.table("interview_sessions").insert(data).execute()
        if not result.data:
            raise RuntimeError("Session insert returned no data")
        return result.data[0]

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = (
                SupabaseClient.get()
                .table("interview_sessions")
                .select("*")
                .eq("id", session_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("SessionRepository.get(%s): %s", session_id, e)
            return None

    def list_for_user(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            result = (
                SupabaseClient.get()
                .table("interview_sessions")
                .select("*")
                .eq("user_id", user_id)
                .order("start_time", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error("SessionRepository.list_for_user(%s): %s", user_id, e)
            return []

    def update_score(self, session_id: str, score: float) -> bool:
        try:
            result = (
                SupabaseClient.get()
                .table("interview_sessions")
                .update({"score": score, "updated_at": _now()})
                .eq("id", session_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error("SessionRepository.update_score(%s): %s", session_id, e)
            return False

    def complete(self, session_id: str, final_score: Optional[float] = None) -> bool:
        try:
            payload: Dict[str, Any] = {
                "status": "COMPLETED",
                "end_time": _now(),
                "updated_at": _now(),
            }
            if final_score is not None:
                payload["score"] = final_score
            result = (
                SupabaseClient.get()
                .table("interview_sessions")
                .update(payload)
                .eq("id", session_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error("SessionRepository.complete(%s): %s", session_id, e)
            return False


# ─────────────────────────────────────────────────────────────────
# Question repository
# ─────────────────────────────────────────────────────────────────

class QuestionRepository:
    def create(self, session_id: str, question_data: Dict[str, Any]) -> Optional[str]:
        """Insert a question row. Returns the new question ID, or None on failure."""
        try:
            row = {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "created_at": _now(),
                **question_data,
            }
            result = (
                SupabaseClient.get()
                .table("interview_questions")
                .insert(row)
                .execute()
            )
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            logger.error("QuestionRepository.create: %s", e)
            return None

    def list_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Fetch questions with nested responses and evaluations."""
        try:
            result = (
                SupabaseClient.get()
                .table("interview_questions")
                .select("*, responses(*, evaluations(*))")
                .eq("session_id", session_id)
                .order("created_at")
                .execute()
            )
            return [_flatten_question(q) for q in (result.data or [])]
        except Exception as e:
            logger.error("QuestionRepository.list_for_session(%s): %s", session_id, e)
            return []


def _flatten_question(q: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten nested response + evaluation into a flat dict for backwards
    compatibility with the orchestrator and analytics layers.
    """
    row = dict(q)
    responses = row.pop("responses", []) or []
    if responses:
        latest_response = responses[-1]
        row["answer_text"] = latest_response.get("response_text")
        evaluations = latest_response.get("evaluations") or []
        if evaluations:
            latest_eval = evaluations[-1]
            row["evaluation_score"] = latest_eval.get("score")
            row["evaluation_feedback"] = latest_eval.get("feedback")
            row["evaluation_details"] = latest_eval.get("evaluation_details")
    return row


# ─────────────────────────────────────────────────────────────────
# Response + Evaluation repository
# ─────────────────────────────────────────────────────────────────

class ResponseRepository:
    def create(self, question_id: str, response_text: str) -> Optional[str]:
        try:
            row = {
                "id": str(uuid.uuid4()),
                "question_id": question_id,
                "response_text": response_text,
                "submitted_at": _now(),
            }
            result = SupabaseClient.get().table("responses").insert(row).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            logger.error("ResponseRepository.create: %s", e)
            return None


class EvaluationRepository:
    def create(self, response_id: str, score: float, feedback: str, details: Dict[str, Any]) -> Optional[str]:
        try:
            row = {
                "id": str(uuid.uuid4()),
                "response_id": response_id,
                "score": score,
                "feedback": feedback,
                "evaluation_details": details,
                "status": "COMPLETED",
            }
            result = SupabaseClient.get().table("evaluations").insert(row).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            logger.error("EvaluationRepository.create: %s", e)
            return None


# ─────────────────────────────────────────────────────────────────
# Code submission + execution repository
# ─────────────────────────────────────────────────────────────────

class CodeSubmissionRepository:
    def create(self, question_id: str, code: str, language: str) -> Optional[str]:
        try:
            row = {
                "id": str(uuid.uuid4()),
                "question_id": question_id,
                "code_text": code,
                "programming_language": language,
                "submitted_at": _now(),
            }
            result = SupabaseClient.get().table("code_submissions").insert(row).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            logger.error("CodeSubmissionRepository.create: %s", e)
            return None


class ExecutionRunRepository:
    def create(self, submission_id: str, status: str, stdout: str, stderr: str) -> Optional[str]:
        try:
            row = {
                "id": str(uuid.uuid4()),
                "code_submission_id": submission_id,
                "status": status,
                "stdout": stdout,
                "stderr": stderr,
            }
            result = SupabaseClient.get().table("execution_runs").insert(row).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            logger.error("ExecutionRunRepository.create: %s", e)
            return None


# ─────────────────────────────────────────────────────────────────
# Skill profile repository
# ─────────────────────────────────────────────────────────────────

class SkillProfileRepository:
    def get(self, user_id: str, skill_name: str) -> Optional[Dict[str, Any]]:
        try:
            result = (
                SupabaseClient.get()
                .table("candidate_skill_profiles")
                .select("*")
                .eq("user_id", user_id)
                .eq("skill_name", skill_name)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("SkillProfileRepository.get: %s", e)
            return None

    def list_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            result = (
                SupabaseClient.get()
                .table("candidate_skill_profiles")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error("SkillProfileRepository.list_for_user: %s", e)
            return []

    def upsert(self, user_id: str, skill_name: str, data: Dict[str, Any]) -> bool:
        try:
            existing = self.get(user_id, skill_name)
            payload = {**data, "updated_at": _now()}
            if existing:
                result = (
                    SupabaseClient.get()
                    .table("candidate_skill_profiles")
                    .update(payload)
                    .eq("id", existing["id"])
                    .execute()
                )
            else:
                payload.update({"id": str(uuid.uuid4()), "user_id": user_id, "skill_name": skill_name})
                result = SupabaseClient.get().table("candidate_skill_profiles").insert(payload).execute()
            return bool(result.data)
        except Exception as e:
            logger.error("SkillProfileRepository.upsert: %s", e)
            return False


# ─────────────────────────────────────────────────────────────────
# Recommendation repository
# ─────────────────────────────────────────────────────────────────

class RecommendationRepository:
    def create_many(self, user_id: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        persisted = []
        for rec in records:
            row = {**rec, "user_id": user_id}
            row.setdefault("id", str(uuid.uuid4()))
            row.setdefault("created_at", _now())
            # Enum → string coercion
            for field in ("status", "strategy", "priority"):
                if hasattr(row.get(field), "value"):
                    row[field] = row[field].value
            try:
                result = SupabaseClient.get().table("recommendations").insert(row).execute()
                persisted.append(result.data[0] if result.data else row)
            except Exception as e:
                logger.warning("RecommendationRepository.create_many insert failed: %s", e)
                persisted.append(row)
        return persisted

    def list_for_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        strategy: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        try:
            q = SupabaseClient.get().table("recommendations").select("*").eq("user_id", user_id)
            if status:
                q = q.eq("status", status.upper())
            if strategy:
                q = q.eq("strategy", strategy)
            result = q.order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error("RecommendationRepository.list_for_user: %s", e)
            return []

    def get(self, recommendation_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = (
                SupabaseClient.get()
                .table("recommendations")
                .select("*")
                .eq("id", recommendation_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("RecommendationRepository.get: %s", e)
            return None

    def update(self, recommendation_id: str, data: Dict[str, Any]) -> bool:
        try:
            payload = {**data, "updated_at": _now()}
            result = (
                SupabaseClient.get()
                .table("recommendations")
                .update(payload)
                .eq("id", recommendation_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.error("RecommendationRepository.update: %s", e)
            return False


# ─────────────────────────────────────────────────────────────────
# Session events + integrity events
# ─────────────────────────────────────────────────────────────────

class SessionEventRepository:
    def create(self, session_id: str, event_type: str, event_data: Dict[str, Any]) -> bool:
        try:
            row = {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "event_type": event_type,
                "event_data": event_data,
                "timestamp": _now(),
            }
            result = SupabaseClient.get().table("session_events").insert(row).execute()
            return bool(result.data)
        except Exception as e:
            logger.error("SessionEventRepository.create: %s", e)
            return False

    def list_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        try:
            result = (
                SupabaseClient.get()
                .table("session_events")
                .select("*")
                .eq("session_id", session_id)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error("SessionEventRepository.list_for_session: %s", e)
            return []


class IntegrityEventRepository:
    def create(self, session_id: str, event_type: str, severity: str, details: Dict[str, Any]) -> bool:
        try:
            row = {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "event_type": event_type,
                "severity": severity,
                "evidence_details": details,
                "timestamp": _now(),
            }
            result = SupabaseClient.get().table("integrity_events").insert(row).execute()
            return bool(result.data)
        except Exception as e:
            logger.error("IntegrityEventRepository.create: %s", e)
            return False

    def list_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        try:
            result = (
                SupabaseClient.get()
                .table("integrity_events")
                .select("*")
                .eq("session_id", session_id)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error("IntegrityEventRepository.list_for_session: %s", e)
            return []


class AIRunRepository:
    def create(
        self,
        session_id: Optional[str],
        prompt_name: str,
        model_version: str,
        latency_ms: int,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        status: str = "COMPLETED",
    ) -> Optional[str]:
        try:
            row = {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "prompt_name": prompt_name,
                "model_version": model_version,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "status": status,
                "created_at": _now(),
            }
            result = SupabaseClient.get().table("ai_runs").insert(row).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            logger.error("AIRunRepository.create: %s", e)
            return None

    def list_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        try:
            result = (
                SupabaseClient.get()
                .table("ai_runs")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at")
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error("AIRunRepository.list_for_session: %s", e)
            return []


# ─────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
