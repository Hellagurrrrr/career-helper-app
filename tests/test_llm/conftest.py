"""Fixtures for the real-AI test suite.

These tests make *real* model calls using the credentials in `.env`, so every
test is skipped automatically when real AI is disabled, no API key is set, or
the optional AI dependencies are not installed. Run them with `-s` to see the
printed model output:

    pytest tests/test_llm -s
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db import reset_all
from app.main import app

OUTPUT_DIR = Path(__file__).parent / "output"


def real_ai_status() -> tuple[bool, str]:
    """Return (available, reason-if-not) for real-AI tests."""
    if not settings.enable_real_ai:
        return False, "CAREER_ENABLE_REAL_AI is not true"
    if not settings.llm_api_key:
        return False, "CAREER_LLM_API_KEY is empty"
    try:  # the optional extras must be importable
        import langchain_openai  # noqa: F401
        import langgraph  # noqa: F401
        import openai  # noqa: F401
    except ImportError as exc:  # pragma: no cover - depends on env
        return False, f"AI dependencies not installed: {exc}"
    return True, ""


@pytest.fixture()
def require_real_ai() -> None:
    ok, reason = real_ai_status()
    if not ok:
        pytest.skip(reason)


@pytest.fixture(scope="session")
def output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


@pytest.fixture()
def save_audio(output_dir: Path):
    """Return a helper that writes audio bytes into the output dir and logs it."""

    def _save(name: str, data: bytes) -> Path:
        path = output_dir / name
        path.write_bytes(data)
        print(f"[saved audio] {path}  ({len(data)} bytes)")
        return path

    return _save


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
    reset_all()


def auth_headers(client: TestClient, email: str = "llm@example.com") -> dict[str, str]:
    resp = client.post(
        "/v1/auth/register",
        json={"name": "LLM Tester", "email": email, "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['tokens']['accessToken']}"}
