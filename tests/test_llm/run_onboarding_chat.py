"""4. Interactive onboarding test.

Talk to the real onboarding model in your terminal. The assistant asks
questions, you type answers, and when it decides it has enough information it
prints the final extracted profile draft.

Two modes:
  - direct: drives app.llm.onboarding.run_step directly (the LLM layer)
  - api:    drives the real API router endpoints (POST /v1/profile/onboarding-chat
            and /answers) through a TestClient

Run from the project root:

    python tests/test_llm/run_onboarding_chat.py          # direct (default)
    python tests/test_llm/run_onboarding_chat.py api      # via API router

Type 'quit' (or press Ctrl-C) to stop early.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running as a plain script (add project root to sys.path).
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.core.config import settings  # noqa: E402
from app.llm.onboarding import run_step  # noqa: E402


def _preflight() -> None:
    if not settings.enable_real_ai:
        sys.exit("CAREER_ENABLE_REAL_AI is not true - enable it in .env first.")
    if not settings.llm_api_key:
        sys.exit("CAREER_LLM_API_KEY is empty - set it in .env first.")
    try:
        import langchain_openai  # noqa: F401
        import langgraph  # noqa: F401
    except ImportError as exc:
        sys.exit(f"AI dependencies not installed: {exc}")


def _read_answer() -> str | None:
    """Read one non-empty answer from the terminal; return None to abort/quit."""
    while True:
        try:
            answer = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[aborted]")
            return None
        if answer.lower() in {"quit", "exit"}:
            print("[stopped early]")
            return None
        if answer:
            return answer
        print("(please type something, or 'quit' to stop)")


def run_direct() -> None:
    """Drive the LLM layer (app.llm.onboarding.run_step) directly."""
    _preflight()
    target = settings.onboarding_target_questions
    print(
        f"=== Onboarding chat - DIRECT (model={settings.llm_onboarding_model}, target~{target}) ==="
    )
    print("Type your answers. Enter 'quit' to stop.\n")

    history: list[tuple[str, str]] = []
    step = run_step([], target)

    while True:
        question = step.get("question") or "(the assistant has no further questions)"
        print(f"Assistant: {question}")

        if step.get("done"):
            break

        answer = _read_answer()
        if answer is None:
            return

        history.append(("ai", question))
        history.append(("human", answer))
        step = run_step(history, target)

    print("\n===== FINAL PROFILE DRAFT =====")
    print(json.dumps(step.get("draft"), ensure_ascii=False, indent=2))


def run_via_api() -> None:
    """Drive the real API router endpoints through a TestClient."""
    _preflight()
    from fastapi.testclient import TestClient

    from app.main import app

    target = settings.onboarding_target_questions
    print(
        f"=== Onboarding chat - API ROUTER (model={settings.llm_onboarding_model}, target~{target}) ==="
    )
    print("Type your answers. Enter 'quit' to stop.\n")

    with TestClient(app) as client:
        reg = client.post(
            "/v1/auth/register",
            json={
                "name": "Onboarding Tester",
                "email": "onboarding-cli@example.com",
                "password": "secret123",
            },
        )
        if reg.status_code != 201:
            sys.exit(f"register failed: {reg.status_code} {reg.text}")
        headers = {"Authorization": f"Bearer {reg.json()['tokens']['accessToken']}"}

        # POST /v1/profile/onboarding-chat -> first question
        session = client.post("/v1/profile/onboarding-chat", headers=headers).json()

        while session.get("status") != "complete":
            question = session.get("question") or "(no question)"
            print(f"Assistant: {question}")

            answer = _read_answer()
            if answer is None:
                return

            # POST /v1/profile/onboarding-chat/answers -> next question or completion
            resp = client.post(
                "/v1/profile/onboarding-chat/answers",
                json={"text": answer},
                headers=headers,
            )
            if resp.status_code != 200:
                print(f"[error] {resp.status_code} {resp.text}")
                continue
            session = resp.json()

        print("\n===== FINAL PROFILE DRAFT (from API) =====")
        print(json.dumps(session.get("draft"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "direct"
    if mode == "api":
        run_via_api()
    elif mode in ("direct", "llm"):
        run_direct()
    else:
        sys.exit("usage: python tests/test_llm/run_onboarding_chat.py [direct|api]")
