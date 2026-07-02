from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration.

    Values can be overridden via environment variables or a local .env file.
    Defaults are dev-friendly so the mock backend runs with zero setup.
    """

    model_config = SettingsConfigDict(env_prefix="CAREER_", env_file=".env", extra="ignore")

    app_name: str = "AI Career Helper API"
    api_prefix: str = "/v1"

    # JWT (>= 32 bytes to satisfy HS256 / RFC 7518; override in production)
    jwt_secret: str = "dev-secret-change-me-in-production-min-32-bytes"
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 30 * 60  # 30 minutes (api-design 2.1)
    refresh_token_ttl_seconds: int = 30 * 24 * 3600  # 30 days

    # Upload limits
    cv_max_bytes: int = 10 * 1024 * 1024  # 10 MB (api-design 3.3)
    audio_max_bytes: int = 25 * 1024 * 1024  # 25 MB (api-design 9.5)

    # Local database. Uses SQLite by default so the demo persists across restarts
    # without requiring an external service.
    local_database_path: str = "app/data/career_helper.sqlite3"

    # Async task simulation: number of polls returning "processing" before "complete"
    async_processing_polls: int = 2

    # Mock interview rounds (api-design 9.6 MOCK_QUESTION_COUNT)
    mock_question_count: int = 4

    # Enable the dev-only reset endpoint (use-case SET-07)
    enable_dev_reset: bool = True

    # -----------------------------------------------------------------------
    # Real AI integration (see plan: real-ai-integration)
    #
    # Master switch. When false (default) every AI capability falls back to the
    # deterministic mock in app/services/mock_ai.py, so the demo and the test
    # suite run with zero external dependencies or API keys.
    # -----------------------------------------------------------------------
    enable_real_ai: bool = False

    # Chat LLM (OpenAI-compatible). base_url lets you point at a proxy or a
    # domestic gateway that speaks the OpenAI protocol.
    llm_api_key: str = ""
    llm_base_url: str | None = None
    llm_temperature: float = 0.2
    llm_timeout: int = 60

    # Per-purpose model names so expensive capabilities can use stronger models.
    llm_cv_model: str = "gpt-4o-mini"
    llm_onboarding_model: str = "gpt-4o-mini"
    llm_tailored_cv_model: str = "gpt-4o"
    llm_interview_model: str = "gpt-4o"

    # Conversational onboarding: how many questions the assistant aims to ask
    # before it stops and produces the profile draft (drives totalQuestions).
    onboarding_target_questions: int = 6

    # Voice (STT/TTS). voice_provider selects the implementation in
    # app/llm/voice.py; only "openai" ships today but the layer is pluggable.
    voice_provider: str = "openai"
    voice_api_key: str = ""  # falls back to llm_api_key when empty
    voice_base_url: str | None = None  # falls back to llm_base_url when empty
    stt_model: str = "whisper-1"
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"


settings = Settings()
