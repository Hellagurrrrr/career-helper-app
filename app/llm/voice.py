"""Pluggable speech layer: STT (transcribe) and TTS (synthesize).

Only the OpenAI implementation ships today, but routers depend on the abstract
``VoiceProvider`` so a domestic provider can be dropped in later by adding a new
class and a branch in ``get_voice_provider``.

The ``openai`` SDK is imported lazily so this module is import-safe in mock mode.
"""

from __future__ import annotations

import io
from abc import ABC, abstractmethod
from functools import cache

from app.core.config import settings


class VoiceProvider(ABC):
    """Speech-to-text and text-to-speech contract."""

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        """Return the transcript text for an uploaded audio clip."""

    @abstractmethod
    def synthesize(self, text: str) -> tuple[bytes, str]:
        """Return ``(audio_bytes, media_type)`` for the spoken form of ``text``."""


class OpenAIVoiceProvider(VoiceProvider):
    """Whisper for transcription, OpenAI TTS for synthesis."""

    def _client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional extra
            raise RuntimeError(
                "openai is not installed. Install the real-AI extras from "
                "requirements.txt to use voice features."
            ) from exc

        api_key = settings.voice_api_key or settings.llm_api_key
        if not api_key:
            raise RuntimeError(
                "Voice features need an API key. Set CAREER_VOICE_API_KEY "
                "(or CAREER_LLM_API_KEY) in your .env."
            )
        base_url = settings.voice_base_url or settings.llm_base_url
        return OpenAI(api_key=api_key, base_url=base_url, timeout=settings.llm_timeout)

    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        buffer = io.BytesIO(audio_bytes)
        buffer.name = filename or "audio.mp3"  # SDK infers the format from the name
        result = self._client().audio.transcriptions.create(
            model=settings.stt_model,
            file=buffer,
        )
        return (getattr(result, "text", "") or "").strip()

    def synthesize(self, text: str) -> tuple[bytes, str]:
        response = self._client().audio.speech.create(
            model=settings.tts_model,
            voice=settings.tts_voice,
            input=text,
        )
        return response.content, "audio/mpeg"


@cache
def get_voice_provider() -> VoiceProvider:
    """Return the configured voice provider (cached)."""
    provider = (settings.voice_provider or "openai").lower()
    if provider == "openai":
        return OpenAIVoiceProvider()
    raise RuntimeError(
        f"Unknown CAREER_VOICE_PROVIDER '{settings.voice_provider}'. Supported: openai."
    )
