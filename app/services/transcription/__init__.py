"""
Transcription service package.

Provides Whisper-based speech-to-text transcription
using the Hugging Face transformers pipeline.
"""
from app.services.transcription.whisper_service import WhisperTranscriptionService

__all__ = ["WhisperTranscriptionService"]
