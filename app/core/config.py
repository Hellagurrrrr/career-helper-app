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

    # JWT
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 30 * 60          # 30 minutes (api-design 2.1)
    refresh_token_ttl_seconds: int = 30 * 24 * 3600  # 30 days

    # Upload limits
    cv_max_bytes: int = 10 * 1024 * 1024     # 10 MB (api-design 3.3)
    audio_max_bytes: int = 25 * 1024 * 1024  # 25 MB (api-design 9.5)

    # Async task simulation: number of polls returning "processing" before "complete"
    async_processing_polls: int = 2

    # Mock interview rounds (api-design 9.6 MOCK_QUESTION_COUNT)
    mock_question_count: int = 4

    # Enable the dev-only reset endpoint (use-case SET-07)
    enable_dev_reset: bool = True


settings = Settings()
