"""
Speech-to-Text Transcription for voice interviews.
Category: PRETRAINED (openai/whisper-base.en).
https://huggingface.co/openai/whisper-base.en

Converts audio bytes/files into candidate text transcripts.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_WHISPER_MODEL = "openai/whisper-base.en"


class VoiceTranscriber:
    """Transcribes spoken candidate audio using Whisper."""

    def __init__(self, model_name: str = DEFAULT_WHISPER_MODEL, device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._pipeline = None
        self._fallback_mode = False

    def _load_model(self):
        if self._pipeline is not None or self._fallback_mode:
            return
        try:
            # Prefer faster-whisper if installed, or transformers pipeline
            try:
                from faster_whisper import WhisperModel
                logger.info("Loading faster-whisper model: %s on %s", self.model_name, self.device)
                self._model = WhisperModel(self.model_name, device=self.device, compute_type="int8")
                return
            except ImportError:
                pass

            from transformers import pipeline
            logger.info("Loading HuggingFace ASR pipeline: %s on %s", self.model_name, self.device)
            self._pipeline = pipeline("automatic-speech-recognition", model=self.model_name, device=self.device)
        except Exception as e:
            logger.warning("Could not load Whisper model (%s): %s. Audio STT unavailable locally.", self.model_name, e)
            self._fallback_mode = True

    def transcribe(self, audio_path_or_bytes: Any) -> Dict[str, Any]:
        """
        Transcribe audio input.
        Returns:
            transcript: str
            confidence: Optional[float]
            method: str
        """
        self._load_model()

        if self._model is not None:
            # faster-whisper
            try:
                segments, info = self._model.transcribe(audio_path_or_bytes, beam_size=5)
                full_text = " ".join([segment.text for segment in segments]).strip()
                return {
                    "transcript": full_text,
                    "language": info.language,
                    "confidence": float(info.language_probability),
                    "method": "faster_whisper_ctranslate2"
                }
            except Exception as e:
                logger.error("faster-whisper transcription failed: %s", e)

        if self._pipeline is not None:
            try:
                res = self._pipeline(audio_path_or_bytes)
                return {
                    "transcript": res.get("text", "").strip(),
                    "language": "en",
                    "confidence": 0.9,
                    "method": "transformers_whisper_pipeline"
                }
            except Exception as e:
                logger.error("Transformers ASR failed: %s", e)

        return {
            "transcript": "",
            "language": "en",
            "confidence": 0.0,
            "error": "Whisper dependencies not installed. Install `pip install faster-whisper` or `transformers torch`.",
            "method": "unsupported_fallback"
        }
