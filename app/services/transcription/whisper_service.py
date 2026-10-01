"""
Whisper-based transcription service using openai/whisper-base.en from Hugging Face.

Responsibilities:
    - Load and cache the Whisper model on first use (lazy singleton)
    - Accept raw audio bytes (WAV/WebM), transcode if needed, run inference
    - Return structured transcription results with confidence and latency metadata
    - NOT persist raw audio — only the transcript and metadata are returned
"""
from __future__ import annotations

import io
import logging
import tempfile
import time
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────

@dataclass
class TranscriptionResult:
    """Structured result from a Whisper transcription run."""
    transcript: str
    language: str
    duration_seconds: float
    model_id: str
    confidence: Optional[float]
    latency_ms: float
    timestamp: str
    segments: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transcript": self.transcript,
            "language": self.language,
            "duration_seconds": self.duration_seconds,
            "model_id": self.model_id,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
            "segments": self.segments,
            "error": self.error,
        }


# ─────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────

_MODEL_ID = "openai/whisper-base.en"


class WhisperTranscriptionService:
    """
    Lazy-loading Whisper transcription service.

    The HF transformers pipeline is loaded on first call to `transcribe()`,
    so cold-start cost is only incurred when the feature is actually used.
    """

    def __init__(self, model_id: str = _MODEL_ID, device: str = "cpu"):
        self._model_id = model_id
        self._device = device
        self._pipeline = None  # loaded lazily

    # ── Model management ────────────────────────────────────────

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    def load_model(self) -> None:
        """Eagerly load the model (useful for health checks or warm-up)."""
        if self._pipeline is not None:
            return
        try:
            from transformers import pipeline as hf_pipeline
            logger.info("Loading Whisper model: %s (device=%s)", self._model_id, self._device)
            t0 = time.time()
            self._pipeline = hf_pipeline(
                "automatic-speech-recognition",
                model=self._model_id,
                device=self._device,
                chunk_length_s=30,
            )
            elapsed = (time.time() - t0) * 1000
            logger.info("Whisper model loaded in %.0f ms", elapsed)
        except ImportError:
            raise RuntimeError(
                "transformers and torch are required for Whisper transcription. "
                "Install them with: pip install transformers torch torchaudio"
            )
        except Exception as exc:
            logger.error("Failed to load Whisper model: %s", exc)
            raise

    def _ensure_loaded(self) -> None:
        if self._pipeline is None:
            self.load_model()

    # ── Audio pre-processing ────────────────────────────────────

    @staticmethod
    def _get_audio_duration(audio_bytes: bytes) -> float:
        """Estimate duration from WAV header or return 0.0 for unknown formats."""
        try:
            with io.BytesIO(audio_bytes) as buf:
                with wave.open(buf, "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    return frames / rate if rate > 0 else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _webm_to_wav(audio_bytes: bytes) -> bytes:
        """
        Convert WebM/Opus audio to WAV using pydub (ffmpeg backend).
        Falls back to returning the original bytes if pydub is unavailable.
        """
        try:
            from pydub import AudioSegment
            segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
            wav_buf = io.BytesIO()
            segment.export(wav_buf, format="wav")
            wav_buf.seek(0)
            return wav_buf.read()
        except ImportError:
            logger.warning("pydub not installed — skipping WebM→WAV conversion")
            return audio_bytes
        except Exception as exc:
            logger.warning("WebM→WAV conversion failed: %s — using raw bytes", exc)
            return audio_bytes

    # ── Core transcription ──────────────────────────────────────

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        content_type: str = "audio/wav",
    ) -> TranscriptionResult:
        """
        Transcribe raw audio bytes and return a structured result.

        Parameters
        ----------
        audio_bytes : bytes
            Raw audio payload. WAV (PCM 16-bit, 16 kHz mono) is preferred.
            WebM/Opus from browser MediaRecorder is also supported via pydub.
        content_type : str
            MIME type of the incoming audio.

        Returns
        -------
        TranscriptionResult
            Contains transcript, confidence, latency, and metadata.
            The `.error` field is set (and `.transcript` is empty) on failure.
        """
        now = datetime.now(timezone.utc).isoformat()

        if not audio_bytes or len(audio_bytes) < 100:
            return TranscriptionResult(
                transcript="",
                language="en",
                duration_seconds=0.0,
                model_id=self._model_id,
                confidence=None,
                latency_ms=0.0,
                timestamp=now,
                error="Audio payload is empty or too small",
            )

        # Convert WebM if necessary
        if "webm" in content_type or "opus" in content_type:
            audio_bytes = self._webm_to_wav(audio_bytes)

        duration = self._get_audio_duration(audio_bytes)

        # Run inference
        try:
            self._ensure_loaded()

            # Write to a temp file — the HF pipeline can read from file paths
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            t0 = time.time()
            result = self._pipeline(
                tmp_path,
                return_timestamps=True,
            )
            latency_ms = (time.time() - t0) * 1000

            # Clean up temp file
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

            # Extract transcript text
            transcript_text = result.get("text", "").strip() if isinstance(result, dict) else str(result).strip()

            # Extract segments / chunks with timestamps
            segments = []
            raw_chunks = result.get("chunks", []) if isinstance(result, dict) else []
            for chunk in raw_chunks:
                segments.append({
                    "text": chunk.get("text", ""),
                    "start": chunk.get("timestamp", [None, None])[0],
                    "end": chunk.get("timestamp", [None, None])[1],
                })

            # Whisper base doesn't expose per-segment logprobs in the HF pipeline,
            # so we set confidence to None (unknown). The frontend will show "N/A".
            confidence = None

            logger.info(
                "Transcription complete: %d chars, %.1f s audio, %.0f ms latency",
                len(transcript_text), duration, latency_ms,
            )

            return TranscriptionResult(
                transcript=transcript_text,
                language="en",
                duration_seconds=round(duration, 2),
                model_id=self._model_id,
                confidence=confidence,
                latency_ms=round(latency_ms, 1),
                timestamp=now,
                segments=segments,
            )

        except Exception as exc:
            logger.error("Transcription failed: %s", exc, exc_info=True)
            return TranscriptionResult(
                transcript="",
                language="en",
                duration_seconds=round(duration, 2),
                model_id=self._model_id,
                confidence=None,
                latency_ms=0.0,
                timestamp=now,
                error=str(exc),
            )

    # ── Health / info ──────────────────────────────────────────

    def get_info(self) -> Dict[str, Any]:
        """Return service metadata for health checks."""
        return {
            "model_id": self._model_id,
            "device": self._device,
            "is_loaded": self.is_loaded,
        }
