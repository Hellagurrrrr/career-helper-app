"""4. Interactive onboarding test.

Talk to the real onboarding model in your terminal. The assistant asks
questions, you type answers, and when it decides it has enough information it
prints the final extracted profile draft.

Run from the project root:

    python tests/test_llm/run_onboarding_chat.py

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


def main() -> None:
    _preflight()
    target = settings.onboarding_target_questions
    print(f"=== Onboarding chat (model={settings.llm_onboarding_model}, target~{target} questions) ===")
    print("Type your answers. Enter 'quit' to stop.\n")

    history: list[tuple[str, str]] = []
    step = run_step([], target)

    while True:
        question = step.get("question") or "(the assistant has no further questions)"
        print(f"Assistant: {question}")

        if step.get("done"):
            break

        try:
            answer = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[aborted]")
            return
        if answer.lower() in {"quit", "exit"}:
            print("[stopped early]")
            return

        history.append(("ai", question))
        history.append(("human", answer))
        step = run_step(history, target)

    draft = step.get("draft")
    print("\n===== FINAL PROFILE DRAFT =====")
    print(json.dumps(draft, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
