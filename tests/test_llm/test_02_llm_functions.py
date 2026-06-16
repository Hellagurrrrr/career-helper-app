"""2. Exercise each function in app/llm with mock data and print the output.

TTS output is written to tests/test_llm/output/.
"""

from __future__ import annotations

import json

import pytest

from app.llm import cv_extraction, interview, onboarding, parsing, tailored_cv, voice
from tests.test_llm.mock_data import (
    MOCK_CV_TEXT,
    MOCK_JOB,
    MOCK_PROFILE,
    MOCK_SPOKEN_ANSWER,
    MOCK_TRANSCRIPT,
)

pytestmark = pytest.mark.usefixtures("require_real_ai")


def _dump(label: str, value) -> None:
    print(f"\n===== {label} =====")
    print(json.dumps(value, ensure_ascii=False, indent=2) if not isinstance(value, str) else value)


def test_parsing_plain_text():
    # parsing has no API cost; verify the txt path round-trips.
    text = parsing.extract_text("resume.txt", MOCK_CV_TEXT.encode("utf-8"))
    _dump("parsing.extract_text (txt)", text[:200] + " ...")
    assert "Jane Doe" in text


def test_cv_extraction():
    draft = cv_extraction.extract_profile_from_cv(MOCK_CV_TEXT)
    _dump("cv_extraction.extract_profile_from_cv", draft)
    assert isinstance(draft, dict)
    assert draft.get("name")
    assert isinstance(draft.get("skills"), list)


def test_tailored_cv():
    result = tailored_cv.generate_tailored_cv(MOCK_PROFILE, MOCK_JOB)
    _dump("tailored_cv.generate_tailored_cv", result)
    assert result["cvText"].strip()
    assert isinstance(result["highlights"], list)


def test_interview_questions():
    questions = interview.generate_questions(MOCK_PROFILE, MOCK_JOB)
    _dump("interview.generate_questions", questions)
    assert questions and all(isinstance(q, str) for q in questions)


def test_interview_scoring():
    analysis = interview.analyze_transcript(MOCK_TRANSCRIPT)
    _dump("interview.analyze_transcript", analysis)
    assert analysis["overallSummary"]
    assert analysis["dimensions"], "expected dimension scores"
    ids = {d["id"] for d in analysis["dimensions"]}
    print("[dimensions]", ids)


def test_onboarding_step():
    # First step from an empty conversation should yield an opening question.
    first = onboarding.run_step([], target_questions=6)
    _dump("onboarding.run_step (empty history)", first)
    assert first["done"] is False
    assert first["question"]

    # A rich, already-answered conversation should let the model wrap up.
    history = [
        ("ai", first["question"]),
        ("human", "My name is Jane Doe."),
        ("ai", "Which school do you attend and what do you study?"),
        ("human", "State University, BSc in Computer Science, graduating 2025."),
        ("ai", "What are your main skills?"),
        ("human", "Python, FastAPI, SQL, React and Docker."),
        ("ai", "Any internships or projects?"),
        ("human", "Interned at Acme Corp on data pipelines; built a course scheduler."),
        ("ai", "Which relevant courses have you taken?"),
        ("human", "Data Structures, Databases and Machine Learning."),
    ]
    later = onboarding.run_step(history, target_questions=6)
    _dump("onboarding.run_step (rich history)", later)
    if later["done"]:
        assert later["draft"] is not None


def test_voice_round_trip(save_audio):
    provider = voice.get_voice_provider()

    # TTS: synthesize an answer and save it.
    audio, media_type = provider.synthesize(MOCK_SPOKEN_ANSWER)
    print(f"\n[tts] media_type={media_type} bytes={len(audio)}")
    assert audio and media_type
    save_audio("llm_function_tts.mp3", audio)

    # STT: transcribe the audio we just produced.
    transcript = provider.transcribe(audio, "llm_function_tts.mp3")
    _dump("voice.transcribe (round-trip)", transcript)
    assert transcript.strip()
