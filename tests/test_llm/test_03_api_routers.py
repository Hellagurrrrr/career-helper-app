"""3. Drive the API routers with mock data (real AI) and print the output.

Coach-question TTS and any uploaded audio are saved to tests/test_llm/output/.
Background tasks run synchronously under TestClient, so a couple of polls are
enough to reach a terminal state.
"""

from __future__ import annotations

import json
import time

import pytest

from app.llm.voice import get_voice_provider
from tests.test_llm.conftest import auth_headers

pytestmark = pytest.mark.usefixtures("require_real_ai")


def _dump(label: str, value) -> None:
    print(f"\n===== {label} =====")
    print(json.dumps(value, ensure_ascii=False, indent=2) if not isinstance(value, str) else value)


@pytest.fixture()
def ctx(client):
    """Register a user and create a goal + standard application."""
    headers = auth_headers(client)
    goal_id = client.post("/v1/goals", json={"catalogId": "1"}, headers=headers).json()["id"]
    app_id = client.post(
        "/v1/applications",
        json={"kind": "standard", "goalId": goal_id, "jobId": "j_102"},
        headers=headers,
    ).json()["id"]
    return {"client": client, "headers": headers, "goal_id": goal_id, "app_id": app_id}


def test_router_tailored_cv(ctx):
    client, headers, goal_id = ctx["client"], ctx["headers"], ctx["goal_id"]
    client.put(
        "/v1/profile", json={"name": "Jane Doe", "skills": ["Python", "FastAPI"]}, headers=headers
    )
    resp = client.post(
        "/v1/tailored-cv/generate",
        json={"jobId": "j_101", "goalId": goal_id},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    _dump("POST /tailored-cv/generate", resp.json())
    assert resp.json()["cvText"].strip()


def test_router_extract_cv(ctx):
    client, headers = ctx["client"], ctx["headers"]
    from tests.test_llm.mock_data import MOCK_CV_TEXT

    files = {"file": ("resume.txt", MOCK_CV_TEXT.encode("utf-8"), "text/plain")}
    start = client.post("/v1/profile/extract-cv", files=files, headers=headers)
    assert start.status_code == 202, start.text
    task_id = start.json()["taskId"]

    result = None
    for _ in range(6):
        result = client.get(f"/v1/profile/extract-cv/{task_id}", headers=headers).json()
        if result["status"] in ("complete", "failed"):
            break
        time.sleep(0.5)
    _dump("GET /profile/extract-cv (final)", result)
    assert result["status"] == "complete", result
    assert result["draft"]["name"]


def test_router_interview_review(ctx, save_audio):
    client, headers, app_id = ctx["client"], ctx["headers"], ctx["app_id"]

    # Build an audio file via TTS, then upload it as the interview recording.
    from tests.test_llm.mock_data import MOCK_SPOKEN_ANSWER

    audio, _ = get_voice_provider().synthesize(MOCK_SPOKEN_ANSWER)
    save_audio("router_review_input.mp3", audio)

    start = client.post(
        f"/v1/applications/{app_id}/interview-reviews",
        files={"file": ("interview.mp3", audio, "audio/mpeg")},
        headers=headers,
    )
    assert start.status_code == 202, start.text
    review_id = start.json()["id"]

    result = None
    for _ in range(8):
        result = client.get(
            f"/v1/applications/{app_id}/interview-reviews/{review_id}", headers=headers
        ).json()
        if result["status"] in ("complete", "failed"):
            break
        time.sleep(0.5)
    _dump("GET interview-review (final)", result)
    assert result["status"] == "complete", result
    assert result["review"]["dimensions"]


def test_router_mock_interview(ctx, save_audio):
    client, headers, app_id = ctx["client"], ctx["headers"], ctx["app_id"]
    client.put("/v1/profile", json={"name": "Jane Doe", "skills": ["Python"]}, headers=headers)

    start = client.post(f"/v1/applications/{app_id}/mock-interviews", headers=headers)
    assert start.status_code == 201, start.text
    session_id = start.json()["sessionId"]
    _dump("POST mock-interviews (start)", start.json())

    # Fetch the session to get the first coach turn id, then pull its TTS audio.
    session = client.get(
        f"/v1/applications/{app_id}/mock-interviews/{session_id}", headers=headers
    ).json()
    coach_turn = next(t for t in session["turns"] if t["role"] == "coach")
    audio_resp = client.get(
        f"/v1/applications/{app_id}/mock-interviews/{session_id}/turns/{coach_turn['id']}/audio",
        headers=headers,
    )
    assert audio_resp.status_code == 200, audio_resp.text
    save_audio("router_coach_question.mp3", audio_resp.content)

    # Answer the first question by text.
    text_turn = client.post(
        f"/v1/applications/{app_id}/mock-interviews/{session_id}/turns",
        json={"text": "I built a FastAPI backend for a course scheduler and owned the API design."},
        headers=headers,
    )
    _dump("POST turns (text answer)", text_turn.json())

    # Answer the next question by voice (TTS -> upload -> STT inside the router).
    from tests.test_llm.mock_data import MOCK_SPOKEN_ANSWER

    answer_audio, _ = get_voice_provider().synthesize(MOCK_SPOKEN_ANSWER)
    save_audio("router_voice_answer.mp3", answer_audio)
    voice_turn = client.post(
        f"/v1/applications/{app_id}/mock-interviews/{session_id}/turns/voice",
        files={"file": ("answer.mp3", answer_audio, "audio/mpeg")},
        data={"end": "false"},
        headers=headers,
    )
    assert voice_turn.status_code == 200, voice_turn.text
    _dump("POST turns/voice (spoken answer)", voice_turn.json())

    # End the interview, then poll until background scoring populates dimensions.
    end = client.post(
        f"/v1/applications/{app_id}/mock-interviews/{session_id}/turns",
        json={"end": True},
        headers=headers,
    )
    _dump("POST turns (end)", end.json())

    final = None
    for _ in range(8):
        final = client.get(
            f"/v1/applications/{app_id}/mock-interviews/{session_id}", headers=headers
        ).json()
        if final["dimensions"]:
            break
        time.sleep(0.5)
    _dump("GET mock-interview (final, scored)", final)
    assert final["dimensions"], "expected scored dimensions after the interview"
