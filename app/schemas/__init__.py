"""
API schemas — Pydantic models for request validation and response serialization.

These live at the API boundary: routes validate incoming JSON against request
schemas, and return data serialized via response schemas.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import uuid


# ─────────────────────────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────────────────────────

VALID_INTERVIEW_TYPES = {
    "Software Engineer",
    "Data Scientist",
    "Product Manager",
    "DevOps Engineer",
    "technical",
    "behavioral",
    "system_design",
    "coding",
}


class StartSessionRequest(BaseModel):
    interview_type: str
    target_role: Optional[str] = None

    @field_validator("interview_type")
    @classmethod
    def validate_interview_type(cls, v: str) -> str:
        if v not in VALID_INTERVIEW_TYPES:
            raise ValueError(f"Unsupported interview type: {v!r}. Valid: {sorted(VALID_INTERVIEW_TYPES)}")
        return v


class SubmitAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer_text: str
    input_modality: Optional[str] = "typed"  # "typed" | "voice"
    transcription_metadata: Optional[Dict[str, Any]] = None

    @field_validator("answer_text")
    @classmethod
    def answer_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("answer_text must not be empty")
        return v.strip()


class SubmitVoiceAnswerRequest(BaseModel):
    """Voice answer submission — carries transcript + transcription metadata."""
    session_id: str
    question_id: str
    transcript: str
    transcription_metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("transcript")
    @classmethod
    def transcript_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("transcript must not be empty")
        return v.strip()


class SubmitCodeRequest(BaseModel):
    session_id: str
    question_id: str
    code: str
    language: str
    run_tests: bool = False

    @field_validator("language")
    @classmethod
    def normalize_language(cls, v: str) -> str:
        return v.strip().lower()


class FollowUpRequest(BaseModel):
    question: str
    answer: str
    interview_type: str


class LogEventRequest(BaseModel):
    session_id: str
    event_type: str
    details: Dict[str, Any] = Field(default_factory=dict)


class LogAnomalyRequest(BaseModel):
    session_id: str
    anomaly_type: str
    severity: str
    details: Dict[str, Any] = Field(default_factory=dict)


class SecurityCheckRequest(BaseModel):
    session_id: str
    events: List[Dict[str, Any]] = Field(default_factory=list)


class UpdateRecommendationStatusRequest(BaseModel):
    status: str
    outcome_score: Optional[float] = None
    outcome_notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        allowed = {"PENDING", "ACCEPTED", "COMPLETED", "DISMISSED"}
        if v.upper() not in allowed:
            raise ValueError(f"Invalid status {v!r}")
        return v.upper()


# ─────────────────────────────────────────────────────────────────
# Response helpers
# ─────────────────────────────────────────────────────────────────

def success(data: Any = None, message: str = "OK", **extra) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"success": True, "error": False, "message": message}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return payload


def error(message: str, code: str = "INTERNAL_ERROR", **extra) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "success": False,
        "error": True,
        "message": message,
        "code": code,
    }
    payload.update(extra)
    return payload
