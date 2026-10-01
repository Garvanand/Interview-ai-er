import io
import os
import time
import uuid
import tempfile
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

@dataclass
class TranscriptionResult:
    transcript: str = ""
    language: str = "en"
    duration_seconds: Optional[float] = None
    model_id: str = "openai/whisper-base.en"
    confidence: Optional[float] = None
    latency_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    segments: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


class WhisperTranscriptionService:
    def __init__(self, model_id: str = "openai/whisper-base.en"):
        self.model_id = model_id
        self.pipeline = None
        self._load_model()

    def _load_model(self):
        try:
            from transformers import pipeline
            import torch
            
            # Using base.en as requested
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            logger.info("Loading Whisper model: %s on %s", self.model_id, device)
            
            # chunk_length_s is useful for longer audio
            self.pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model_id,
                chunk_length_s=30,
                device=device,
            )
            logger.info("Whisper model loaded successfully.")
        except ImportError as e:
            logger.error("Failed to import transformers or torch: %s", e)
        except Exception as e:
            logger.exception("Failed to load Whisper model: %s", e)

    def transcribe(self, audio_bytes: bytes, content_type: str = "audio/wav") -> TranscriptionResult:
        """
        Transcribe audio bytes using Whisper.
        """
        start_time = time.time()
        
        if not self.pipeline:
            return TranscriptionResult(error="Transcription model not loaded (check transformers/torch)")
            
        if not audio_bytes:
            return TranscriptionResult(error="Empty audio data")
            
        # Determine extension
        ext = ".wav"
        if "webm" in content_type:
            ext = ".webm"
        elif "mp3" in content_type:
            ext = ".mp3"
            
        # Write to temporary file
        fd, temp_path = tempfile.mkstemp(suffix=ext)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(audio_bytes)
                
            # Perform transcription
            # We can request timestamps by passing return_timestamps=True
            output = self.pipeline(temp_path, return_timestamps=True)
            
            transcript = output.get("text", "").strip()
            chunks = output.get("chunks", [])
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Approximate duration based on chunks if available, or just leave None
            duration = None
            if chunks and chunks[-1].get("timestamp"):
                end_ts = chunks[-1]["timestamp"][1]
                if end_ts is not None:
                    duration = float(end_ts)
            
            return TranscriptionResult(
                transcript=transcript,
                language="en", # whisper-base.en is English only
                duration_seconds=duration,
                model_id=self.model_id,
                confidence=None, # Whisper pipeline doesn't natively return confidence per segment by default in this mode
                latency_ms=latency_ms,
                segments=chunks,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
        except Exception as e:
            logger.exception("Transcription failed")
            return TranscriptionResult(error=str(e))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
