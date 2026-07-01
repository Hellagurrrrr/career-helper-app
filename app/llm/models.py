"""Chat-model factory.

Returns a configured, cached ``ChatOpenAI`` per capability so expensive tasks
(writing, scoring) can use a stronger model than cheap ones (extraction).

``langchain_openai`` is imported lazily so importing this module never fails in
mock mode; only ``get_llm`` requires the package to be installed.
"""

from __future__ import annotations

from enum import Enum
from functools import cache
from typing import Any

from app.core.config import settings


class Purpose(str, Enum):
    """A capability that needs a chat model."""

    CV = "cv"
    ONBOARDING = "onboarding"
    TAILORED_CV = "tailored_cv"
    INTERVIEW = "interview"


_MODEL_FOR: dict[Purpose, str] = {
    Purpose.CV: "llm_cv_model",
    Purpose.ONBOARDING: "llm_onboarding_model",
    Purpose.TAILORED_CV: "llm_tailored_cv_model",
    Purpose.INTERVIEW: "llm_interview_model",
}


@cache
def get_llm(purpose: Purpose) -> Any:
    """Build (and cache) a ChatOpenAI instance for the given purpose.

    Raises a clear error when real AI is misconfigured rather than failing deep
    inside a request handler.
    """
    if not settings.llm_api_key:
        raise RuntimeError(
            "Real AI is enabled but CAREER_LLM_API_KEY is empty. "
            "Set it in your .env or disable CAREER_ENABLE_REAL_AI."
        )

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError(
            "langchain-openai is not installed. Install the real-AI extras from "
            "requirements.txt (langchain, langchain-openai, ...)."
        ) from exc

    model_name = getattr(settings, _MODEL_FOR[purpose])
    return ChatOpenAI(
        model=model_name,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout,
    )
