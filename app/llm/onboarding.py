"""Conversational onboarding as a small LangGraph.

Graph: ``decide`` (ask the next question or judge that enough was collected) ->
conditional edge -> ``extract`` (structured ProfileDraft) when done, else END.

HTTP is stateless, so the router replays the stored conversation on every turn
and runs the graph once; the graph itself holds no cross-request state.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, TypedDict


class _State(TypedDict, total=False):
    history: list[tuple[str, str]]  # ("ai" | "human", text)
    target_questions: int
    questions_asked: int
    done: bool
    question: str
    draft: dict[str, Any] | None


@lru_cache(maxsize=1)
def _graph():
    from langgraph.graph import END, StateGraph

    from app.llm.io_schemas import OnboardingStep, ProfileDraft
    from app.llm.models import Purpose, get_llm
    from app.llm.prompts import ONBOARDING_EXTRACTION_SYSTEM, ONBOARDING_SYSTEM

    def decide(state: _State) -> _State:
        target = state["target_questions"]
        # `target` is a soft guide; this hard cap only exists so a runaway
        # conversation always terminates.
        hard_cap = max(target * 2, target + 4)
        llm = get_llm(Purpose.ONBOARDING).with_structured_output(OnboardingStep)
        guidance = (
            f"{ONBOARDING_SYSTEM}\n\nAim for roughly {target} questions, but prioritise a "
            "natural flow and completeness over hitting an exact count."
        )
        messages: list[tuple[str, str]] = [("system", guidance), *state["history"]]
        step: OnboardingStep = llm.invoke(messages)
        done = bool(step.done) or state["questions_asked"] >= hard_cap
        return {"done": done, "question": "" if done else step.question.strip()}

    def extract(state: _State) -> _State:
        llm = get_llm(Purpose.ONBOARDING).with_structured_output(ProfileDraft)
        convo = "\n".join(f"{'Assistant' if r == 'ai' else 'User'}: {t}" for r, t in state["history"])
        draft: ProfileDraft = llm.invoke(
            [
                ("system", ONBOARDING_EXTRACTION_SYSTEM),
                ("human", f"Conversation:\n{convo}\n\nExtract the candidate's profile."),
            ]
        )
        return {"draft": draft.model_dump()}

    builder = StateGraph(_State)
    builder.add_node("decide", decide)
    builder.add_node("extract", extract)
    builder.set_entry_point("decide")
    builder.add_conditional_edges(
        "decide",
        lambda s: "extract" if s["done"] else "end",
        {"extract": "extract", "end": END},
    )
    builder.add_edge("extract", END)
    return builder.compile()


def run_step(history: list[tuple[str, str]], target_questions: int) -> dict[str, Any]:
    """Advance the onboarding conversation by one assistant turn.

    ``history`` is the full conversation as ``("ai"|"human", text)`` pairs.
    Returns ``{done, question, draft}``.
    """
    questions_asked = sum(1 for role, _ in history if role == "ai")
    result = _graph().invoke(
        {
            "history": history,
            "target_questions": target_questions,
            "questions_asked": questions_asked,
            "done": False,
            "question": "",
            "draft": None,
        }
    )
    return {
        "done": bool(result.get("done")),
        "question": result.get("question") or "",
        "draft": result.get("draft"),
    }
