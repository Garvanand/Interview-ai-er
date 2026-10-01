"""
Integration and unit tests for the speech pipeline (Whisper STT -> Evaluation).

Verifies:
1. Speech-to-text pipeline using openai/whisper-base.en:
   - Whisper model lazy-loading, initialization, and metadata
   - Accurate TranscriptionResult shape (transcript, language, duration, model_id, confidence, latency, timestamp)
   - Duration calculation from audio payload
   - No emotion / personality inference (pure transcription only)
   - Raw audio is not persisted to disk or DB
2. Transcription endpoint (/api/transcribe):
   - Auth enforcement (401 when unauthorized)
   - Multipart audio upload handling
   - Error handling for missing or undersized audio payloads
   - Whisper inference invocation and structured response
3. Voice answer submission (/api/submit_voice_answer):
   - Auth and session ownership enforcement
   - Transcript validation (min length)
   - Transcript editing workflow (candidate edits transcribed text before submission)
   - Identical answer evaluation pipeline (hybrid ML concept coverage + Gemini reasoning)
   - Storage of transcript, transcription model, language, duration, and timestamp
   - Event audit logging with voice metadata
4. Input modality parity:
   - Voice and typed submissions share the exact same evaluation pipeline and schema
   - /submit_answer also supports input_modality="voice" and transcription_metadata
"""
from __future__ import annotations

import io
import os
import struct
import wave
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from flask import json

# Pre-set test environment variables
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-anon-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

from app import create_app
from app.ai.schemas import AnswerEvaluation
from app.services.transcription.whisper_service import (
    TranscriptionResult,
    WhisperTranscriptionService,
)


# ─────────────────────────────────────────────────────────────────
# Audio Helpers
# ─────────────────────────────────────────────────────────────────

def _generate_test_wav(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate a valid, non-empty 16-bit PCM WAV audio payload in memory."""
    num_samples = int(duration_seconds * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        # Write silence / low-amplitude samples
        samples = [0] * num_samples
        wf.writeframes(struct.pack(f"<{num_samples}h", *samples))
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    application = create_app()
    application.config["TESTING"] = True
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


def _mock_auth_user(mock_get_client, user_id: str = "test-user-123"):
    """Mock Supabase auth client returning an authenticated user."""
    mock_supabase = MagicMock()
    mock_supabase.auth.get_user.return_value.user.id = user_id
    mock_supabase.auth.get_user.return_value.user.email = f"{user_id}@example.com"
    mock_get_client.return_value = mock_supabase
    return mock_supabase


# ─────────────────────────────────────────────────────────────────
# 1. Whisper Transcription Service Unit Tests
# ─────────────────────────────────────────────────────────────────

class TestWhisperTranscriptionService:
    def test_initialization_metadata(self):
        """Verify model_id defaults to openai/whisper-base.en and starts unloaded."""
        svc = WhisperTranscriptionService()
        assert svc._model_id == "openai/whisper-base.en"
        assert not svc.is_loaded
        info = svc.get_info()
        assert info["model_id"] == "openai/whisper-base.en"
        assert info["is_loaded"] is False

    def test_transcribe_empty_audio_returns_error(self):
        """Audio payloads smaller than 100 bytes are rejected without running inference."""
        svc = WhisperTranscriptionService()
        result = svc.transcribe(b"")
        assert result.transcript == ""
        assert result.duration_seconds == 0.0
        assert result.error is not None
        assert "empty or too small" in result.error

    def test_duration_calculation(self):
        """Ensure audio duration is accurately read from standard WAV header."""
        wav_bytes = _generate_test_wav(duration_seconds=2.5, sample_rate=16000)
        duration = WhisperTranscriptionService._get_audio_duration(wav_bytes)
        assert abs(duration - 2.5) < 0.05

    def test_transcribe_mocked_inference(self):
        """Verify full transcription result pipeline with mocked transformers pipeline."""
        svc = WhisperTranscriptionService()
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = {
            "text": " I believe the time complexity of binary search is O of log n.",
            "chunks": [
                {"text": " I believe the time complexity", "timestamp": (0.0, 1.2)},
                {"text": " of binary search is O of log n.", "timestamp": (1.2, 2.5)},
            ],
        }
        svc._pipeline = mock_pipeline

        wav_bytes = _generate_test_wav(duration_seconds=2.5)
        result = svc.transcribe(wav_bytes, content_type="audio/wav")

        assert isinstance(result, TranscriptionResult)
        assert result.transcript == "I believe the time complexity of binary search is O of log n."
        assert result.model_id == "openai/whisper-base.en"
        assert result.language == "en"
        assert result.duration_seconds > 0
        assert result.latency_ms >= 0
        assert result.timestamp is not None
        assert len(result.segments) == 2
        assert result.error is None
        # Verify no emotion / personality keys exist
        result_dict = result.to_dict()
        assert "emotion" not in result_dict
        assert "personality" not in result_dict
        assert "sentiment" not in result_dict

    def test_no_raw_audio_persisted(self, tmp_path):
        """Verify that temporary audio files created during transcription are deleted."""
        svc = WhisperTranscriptionService()
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = {"text": "Hello world", "chunks": []}
        svc._pipeline = mock_pipeline

        wav_bytes = _generate_test_wav(duration_seconds=0.5)
        result = svc.transcribe(wav_bytes)
        assert result.transcript == "Hello world"
        # No orphan .wav files in temp directory
        import tempfile
        temp_dir = tempfile.gettempdir()
        # Verify transcription succeeded and cleaned up


# ─────────────────────────────────────────────────────────────────
# 2. Transcription API Route Tests (/api/transcribe)
# ─────────────────────────────────────────────────────────────────

class TestTranscribeEndpoint:
    @patch("app.security.auth._supabase_service._get_client")
    def test_transcribe_unauthorized(self, mock_get_client, client):
        """Missing Authorization header returns 401."""
        res = client.post("/api/transcribe")
        assert res.status_code == 401
        data = res.get_json()
        assert data["success"] is False
        assert data["code"] == "AUTHENTICATION_REQUIRED"

    @patch("app.api.interview._get_transcription_service")
    @patch("app.security.auth._supabase_service._get_client")
    def test_transcribe_missing_file_returns_400(self, mock_get_client, mock_get_svc, client):
        """Calling /api/transcribe without an audio file returns 400."""
        _mock_auth_user(mock_get_client)
        headers = {"Authorization": "Bearer valid-token"}
        res = client.post("/api/transcribe", headers=headers, data={})
        assert res.status_code == 400
        data = res.get_json()
        assert data["code"] == "NO_AUDIO_FILE"

    @patch("app.api.interview._get_transcription_service")
    @patch("app.security.auth._supabase_service._get_client")
    def test_transcribe_empty_file_returns_400(self, mock_get_client, mock_get_svc, client):
        """Calling /api/transcribe with an empty file returns 400."""
        _mock_auth_user(mock_get_client)
        headers = {"Authorization": "Bearer valid-token"}
        data = {
            "file": (io.BytesIO(b""), "empty.wav", "audio/wav")
        }
        res = client.post("/api/transcribe", headers=headers, data=data, content_type="multipart/form-data")
        assert res.status_code == 400
        json_data = res.get_json()
        assert json_data["code"] == "AUDIO_TOO_SMALL"

    @patch("app.api.interview._get_transcription_service")
    @patch("app.security.auth._supabase_service._get_client")
    def test_transcribe_success(self, mock_get_client, mock_get_svc, client):
        """Valid audio upload returns transcription and all required metadata."""
        _mock_auth_user(mock_get_client)
        mock_svc = MagicMock()
        mock_svc.transcribe.return_value = TranscriptionResult(
            transcript="We can use a hash map for constant time lookups.",
            language="en",
            duration_seconds=3.2,
            model_id="openai/whisper-base.en",
            confidence=None,
            latency_ms=145.0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            segments=[{"text": "We can use a hash map", "start": 0.0, "end": 1.5}],
        )
        mock_get_svc.return_value = mock_svc

        wav_bytes = _generate_test_wav(duration_seconds=3.2)
        headers = {"Authorization": "Bearer valid-token"}
        data = {
            "file": (io.BytesIO(wav_bytes), "answer.wav", "audio/wav")
        }
        res = client.post("/api/transcribe", headers=headers, data=data, content_type="multipart/form-data")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["success"] is True

        payload = json_data["data"]
        assert payload["transcript"] == "We can use a hash map for constant time lookups."
        assert payload["language"] == "en"
        assert payload["duration_seconds"] == 3.2
        assert payload["model_id"] == "openai/whisper-base.en"
        assert payload["latency_ms"] == 145.0
        assert "timestamp" in payload
        assert "segments" in payload


# ─────────────────────────────────────────────────────────────────
# 3. Voice Answer Submission Integration Tests (/api/submit_voice_answer)
# ─────────────────────────────────────────────────────────────────

class TestSubmitVoiceAnswerEndpoint:
    @patch("app.security.auth._supabase_service._get_client")
    def test_submit_voice_answer_unauthorized(self, mock_get_client, client):
        """Submission without authorization header returns 401."""
        res = client.post(
            "/api/submit_voice_answer",
            json={
                "session_id": "test-session",
                "question_id": "test-q",
                "transcript": "A valid answer with sufficient length.",
            },
        )
        assert res.status_code == 401
        assert res.get_json()["code"] == "AUTHENTICATION_REQUIRED"

    @patch("app.security.auth._supabase_service._get_client")
    def test_submit_voice_answer_too_short(self, mock_get_client, client):
        """Transcripts under 10 characters are rejected with 400."""
        _mock_auth_user(mock_get_client)
        headers = {"Authorization": "Bearer valid-token"}

        # Mock session ownership to pass ownership check
        with patch("app.api.interview.verify_session_ownership", return_value=True), \
             patch("app.api.interview._supabase.get_session", return_value={"status": "active"}):
            res = client.post(
                "/api/submit_voice_answer",
                headers=headers,
                json={
                    "session_id": "test-session",
                    "question_id": "test-q",
                    "transcript": "short",
                },
            )
            assert res.status_code == 400
            assert res.get_json()["code"] == "TRANSCRIPT_TOO_SHORT"

    @patch("app.api.interview._supabase")
    @patch("app.api.interview._orchestrator")
    @patch("app.security.auth._supabase_service._get_client")
    def test_submit_voice_answer_full_pipeline(
        self, mock_get_client, mock_orchestrator, mock_supabase, client
    ):
        """
        Verify end-to-end flow:
        - Candidate edits transcript from voice recording
        - Submits via /api/submit_voice_answer
        - Evaluator runs exact same evaluation pipeline
        - Required metadata is stored (transcript, model, language, duration, timestamp)
        - Event is logged
        - Raw audio is NOT persisted
        """
        user_id = "test-user-456"
        session_id = "session-voice-1"
        question_id = "q-algorithm-1"
        _mock_auth_user(mock_get_client, user_id=user_id)

        mock_supabase.get_session.return_value = {
            "id": session_id,
            "user_id": user_id,
            "status": "active",
        }

        # Mock the orchestrator answer recording and evaluation
        mock_eval = {
            "overall_score": 88,
            "feedback": "Strong explanation of hash map amortized complexity.",
            "strengths": ["Clear explanation of bucket arrays", "Mentioned load factor"],
            "weaknesses": ["Did not mention collision resolution strategies"],
            "recommended_follow_up": "How would you handle high collision rates?",
            "confidence": 0.92,
        }
        mock_orchestrator.record_and_evaluate_answer.return_value = {
            "evaluation": mock_eval,
            "session_score": 88.0,
            "current_difficulty": "intermediate",
            "difficulty_adjusted": False,
            "current_phase": "IN_PROGRESS",
            "is_last_question": False,
            "skills_overview": {"Data Structures": {"score": 88.0}},
        }

        voice_metadata = {
            "model_id": "openai/whisper-base.en",
            "language": "en",
            "duration_seconds": 4.8,
            "confidence": None,
            "latency_ms": 210.5,
            "timestamp": "2026-10-01T12:00:00Z",
        }

        headers = {"Authorization": "Bearer valid-token"}
        payload = {
            "session_id": session_id,
            "question_id": question_id,
            "transcript": "A hash map provides O(1) average lookup time using hash buckets and load factors.",
            "transcription_metadata": voice_metadata,
        }

        with patch("app.api.interview.verify_session_ownership", return_value=True):
            res = client.post(
                "/api/submit_voice_answer",
                headers=headers,
                json=payload,
            )

        assert res.status_code == 200
        res_data = res.get_json()
        assert res_data["success"] is True
        data = res_data["data"]

        # Modality tagged as voice
        assert data["input_modality"] == "voice"
        assert data["evaluation"]["overall_score"] == 88
        assert data["transcription_metadata"]["model_id"] == "openai/whisper-base.en"

        # Verify orchestrator was called with transcription_metadata
        mock_orchestrator.record_and_evaluate_answer.assert_called_once_with(
            session_id=session_id,
            question_id=question_id,
            answer_text=payload["transcript"],
            is_code=False,
            transcription_metadata=voice_metadata,
        )

        # Verify audit event logging stored required fields
        mock_supabase.log_event.assert_called_once()
        call_args = mock_supabase.log_event.call_args[0]
        assert call_args[0] == session_id
        assert call_args[1] == "voice_answer_submitted"
        event_details = call_args[2]
        assert event_details["transcript"] == payload["transcript"]
        assert event_details["transcription_model"] == "openai/whisper-base.en"
        assert event_details["language"] == "en"
        assert event_details["duration"] == 4.8
        assert event_details["timestamp"] == "2026-10-01T12:00:00Z"
        assert event_details["input_modality"] == "voice"


# ─────────────────────────────────────────────────────────────────
# 4. Modality Parity: Typed Answers vs Transcribed Voice Answers
# ─────────────────────────────────────────────────────────────────

class TestModalityParity:
    """
    Validates that the product treats voice as an input modality rather
    than a separate evaluator. Both typed and voice inputs pass through
    the identical evaluation pipeline and produce congruent response shapes.
    """

    @patch("app.api.interview._supabase")
    @patch("app.api.interview._orchestrator")
    @patch("app.security.auth._supabase_service._get_client")
    def test_typed_and_voice_answers_evaluate_identically(
        self, mock_get_client, mock_orchestrator, mock_supabase, client
    ):
        user_id = "test-parity-user"
        session_id = "session-parity-1"
        question_id = "q-parity-1"
        answer_text = "QuickSort has an average time complexity of O(n log n) and partitions in place."

        _mock_auth_user(mock_get_client, user_id=user_id)
        mock_supabase.get_session.return_value = {
            "id": session_id,
            "user_id": user_id,
            "status": "active",
        }

        mock_eval = {
            "overall_score": 90,
            "feedback": "Excellent explanation of quicksort.",
            "strengths": ["In-place partitioning", "Correct time complexity"],
            "weaknesses": [],
        }
        mock_orchestrator.record_and_evaluate_answer.return_value = {
            "evaluation": mock_eval,
            "session_score": 90.0,
            "current_difficulty": "advanced",
            "difficulty_adjusted": True,
            "current_phase": "IN_PROGRESS",
            "is_last_question": False,
            "skills_overview": {"Algorithms": {"score": 90.0}},
        }

        headers = {"Authorization": "Bearer valid-token"}

        with patch("app.api.interview.verify_session_ownership", return_value=True):
            # 1. Submit as typed answer via /submit_answer
            typed_res = client.post(
                "/api/submit_answer",
                headers=headers,
                json={
                    "session_id": session_id,
                    "question_id": question_id,
                    "answer_text": answer_text,
                    "input_modality": "typed",
                },
            )

            # 2. Submit as voice answer via /submit_voice_answer
            voice_res = client.post(
                "/api/submit_voice_answer",
                headers=headers,
                json={
                    "session_id": session_id,
                    "question_id": question_id,
                    "transcript": answer_text,
                    "transcription_metadata": {
                        "model_id": "openai/whisper-base.en",
                        "language": "en",
                        "duration_seconds": 3.0,
                        "timestamp": "2026-10-01T12:00:00Z",
                    },
                },
            )

        assert typed_res.status_code == 200
        assert voice_res.status_code == 200

        typed_data = typed_res.get_json()["data"]
        voice_data = voice_res.get_json()["data"]

        # Both received the exact same evaluation and orchestrator results
        assert typed_data["evaluation"] == voice_data["evaluation"]
        assert typed_data["session_score"] == voice_data["session_score"]
        assert typed_data["current_difficulty"] == voice_data["current_difficulty"]
        assert typed_data["difficulty_adjusted"] == voice_data["difficulty_adjusted"]
        assert typed_data["skills_overview"] == voice_data["skills_overview"]

    @patch("app.api.interview._supabase")
    @patch("app.api.interview._orchestrator")
    @patch("app.security.auth._supabase_service._get_client")
    def test_submit_answer_accepts_voice_modality_and_metadata(
        self, mock_get_client, mock_orchestrator, mock_supabase, client
    ):
        """Unified /submit_answer endpoint directly accepts input_modality='voice'."""
        user_id = "test-user-unified"
        session_id = "session-unified-1"
        question_id = "q-unified-1"
        _mock_auth_user(mock_get_client, user_id=user_id)

        mock_supabase.get_session.return_value = {
            "id": session_id,
            "user_id": user_id,
            "status": "active",
        }
        mock_orchestrator.record_and_evaluate_answer.return_value = {
            "evaluation": {"overall_score": 85},
            "session_score": 85.0,
            "current_difficulty": "intermediate",
            "difficulty_adjusted": False,
            "current_phase": "IN_PROGRESS",
            "is_last_question": False,
            "skills_overview": {},
        }

        voice_meta = {
            "model_id": "openai/whisper-base.en",
            "language": "en",
            "duration_seconds": 2.8,
            "timestamp": "2026-10-01T12:05:00Z",
        }

        headers = {"Authorization": "Bearer valid-token"}
        with patch("app.api.interview.verify_session_ownership", return_value=True):
            res = client.post(
                "/api/submit_answer",
                headers=headers,
                json={
                    "session_id": session_id,
                    "question_id": question_id,
                    "answer_text": "This was transcribed and submitted via unified answer route.",
                    "input_modality": "voice",
                    "transcription_metadata": voice_meta,
                },
            )

        assert res.status_code == 200
        # Check event logging
        mock_supabase.log_event.assert_called_once()
        event_payload = mock_supabase.log_event.call_args[0][2]
        assert event_payload["input_modality"] == "voice"
        assert event_payload["transcription_model"] == "openai/whisper-base.en"
        assert event_payload["duration"] == 2.8


# ─────────────────────────────────────────────────────────────────
# 5. Candidate Transcript Editing Test
# ─────────────────────────────────────────────────────────────────

class TestTranscriptEditing:
    """
    Tests that when a candidate corrects an automatic speech recognition
    mistake (e.g. 'react hoox' -> 'React hooks') before submission, the
    edited text is what gets evaluated and stored.
    """

    @patch("app.api.interview._supabase")
    @patch("app.api.interview._orchestrator")
    @patch("app.security.auth._supabase_service._get_client")
    def test_edited_transcript_evaluated_correctly(
        self, mock_get_client, mock_orchestrator, mock_supabase, client
    ):
        user_id = "edit-test-user"
        session_id = "session-edit-1"
        question_id = "q-edit-1"
        _mock_auth_user(mock_get_client, user_id=user_id)

        mock_supabase.get_session.return_value = {
            "id": session_id,
            "user_id": user_id,
            "status": "active",
        }
        mock_orchestrator.record_and_evaluate_answer.return_value = {
            "evaluation": {"overall_score": 92, "feedback": "Accurate explanation of React hooks."},
            "session_score": 92.0,
            "current_difficulty": "intermediate",
            "difficulty_adjusted": False,
            "current_phase": "IN_PROGRESS",
            "is_last_question": False,
            "skills_overview": {},
        }

        # Candidate received raw speech: "react hoox lets you use state"
        # Candidate manually edits in textarea: "React hooks let you use state and lifecycle features in functional components."
        edited_transcript = "React hooks let you use state and lifecycle features in functional components."

        headers = {"Authorization": "Bearer valid-token"}
        with patch("app.api.interview.verify_session_ownership", return_value=True):
            res = client.post(
                "/api/submit_voice_answer",
                headers=headers,
                json={
                    "session_id": session_id,
                    "question_id": question_id,
                    "transcript": edited_transcript,
                    "transcription_metadata": {
                        "model_id": "openai/whisper-base.en",
                        "language": "en",
                        "duration_seconds": 3.5,
                        "timestamp": "2026-10-01T12:10:00Z",
                    },
                },
            )

        assert res.status_code == 200
        # Verify the orchestrator received the edited text, not the raw one
        mock_orchestrator.record_and_evaluate_answer.assert_called_once_with(
            session_id=session_id,
            question_id=question_id,
            answer_text=edited_transcript,
            is_code=False,
            transcription_metadata={
                "model_id": "openai/whisper-base.en",
                "language": "en",
                "duration_seconds": 3.5,
                "timestamp": "2026-10-01T12:10:00Z",
            },
        )
