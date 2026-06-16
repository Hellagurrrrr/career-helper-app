"""1. Model import + live API connectivity using the key from .env."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.llm.models import Purpose, get_llm


@pytest.mark.usefixtures("require_real_ai")
def test_models_import_and_factory():
    """Every purpose builds a chat model without raising."""
    for purpose in Purpose:
        llm = get_llm(purpose)
        assert llm is not None
        print(f"[factory] {purpose.value} -> {getattr(llm, 'model_name', llm)}")


@pytest.mark.usefixtures("require_real_ai")
def test_live_api_call():
    """A tiny real call proves the .env API key works end-to-end."""
    llm = get_llm(Purpose.CV)
    response = llm.invoke("Reply with exactly the word: pong")
    text = getattr(response, "content", response)
    print(f"\n[connectivity] model={settings.llm_cv_model} reply={text!r}")
    assert isinstance(text, str)
    assert text.strip() != ""
