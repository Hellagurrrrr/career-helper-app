"""CV text -> structured profile draft (real model)."""

from __future__ import annotations

from typing import Any


def extract_profile_from_cv(cv_text: str) -> dict[str, Any]:
    from app.llm.io_schemas import ProfileDraft
    from app.llm.models import Purpose, get_llm
    from app.llm.prompts import CV_EXTRACTION_SYSTEM

    text = (cv_text or "").strip()
    if not text:
        return ProfileDraft().model_dump()

    llm = get_llm(Purpose.CV).with_structured_output(ProfileDraft)
    draft: ProfileDraft = llm.invoke(
        [
            ("system", CV_EXTRACTION_SYSTEM),
            ("human", f"Resume text:\n\n{text}"),
        ]
    )
    return draft.model_dump()
