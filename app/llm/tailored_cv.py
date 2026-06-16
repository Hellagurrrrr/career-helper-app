"""Profile + job -> tailored CV (real model)."""

from __future__ import annotations

import json
from typing import Any


def generate_tailored_cv(profile: dict[str, Any] | None, job: dict[str, Any]) -> dict[str, Any]:
    from app.llm.io_schemas import TailoredCv
    from app.llm.models import Purpose, get_llm
    from app.llm.prompts import TAILORED_CV_SYSTEM

    profile_json = json.dumps(profile or {}, ensure_ascii=False, indent=2)
    job_json = json.dumps(
        {
            "title": job.get("title"),
            "company": job.get("company"),
            "skills": job.get("skills", []),
            "description": job.get("description"),
        },
        ensure_ascii=False,
        indent=2,
    )

    llm = get_llm(Purpose.TAILORED_CV).with_structured_output(TailoredCv)
    result: TailoredCv = llm.invoke(
        [
            ("system", TAILORED_CV_SYSTEM),
            ("human", f"Candidate profile:\n{profile_json}\n\nTarget job:\n{job_json}"),
        ]
    )
    return {"cvText": result.cv_text, "highlights": result.highlights}
