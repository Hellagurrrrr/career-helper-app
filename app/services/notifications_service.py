from __future__ import annotations

from typing import Any

from app.core.security import new_id, now_ms
from app.db import get_connection
from app.repositories import notifications as notifications_repo


def push(
    user_id: str,
    *,
    type: str,
    severity: str,
    title: str,
    body: str,
    link: str | None = None,
    dedup_key: str | None = None,
) -> dict[str, Any] | None:
    """Create a notification, de-duplicating by (user_id, dedupKey).

    Returns the created notification, or None if it was a duplicate. This service
    is called from non-DI contexts (other services, background tasks), so it pulls
    the shared connection directly and commits the write -- mirroring the old
    store's commit-on-save behavior.
    """
    conn = get_connection()
    notification = notifications_repo.add(
        conn,
        user_id,
        notification_id=new_id("n"),
        type=type,
        severity=severity,
        title=title,
        body=body,
        created_at=now_ms(),
        link=link,
        dedup_key=dedup_key,
    )
    conn.commit()
    return notification


def welcome(user_id: str, name: str) -> dict[str, Any] | None:
    """Emit the onboarding welcome notification (use-cases OB-03/04/13)."""
    display = name.strip() or "Friend"
    return push(
        user_id,
        type="system",
        severity="success",
        title="Welcome to AI Career Helper",
        body=f"Welcome, {display}! Let's start building your career plan.",
        link="/",
    )


def check_milestone(
    user_id: str, goal_id: str, old_progress: int, new_progress: int, goal_title: str
) -> None:
    """Emit milestone notifications when progress crosses 25/50/75/100 (NT-05)."""
    for milestone in (25, 50, 75, 100):
        if old_progress < milestone <= new_progress:
            push(
                user_id,
                type="milestone",
                severity="success",
                title=f"{milestone}% milestone reached",
                body=f"You hit {milestone}% on {goal_title}. Keep it up!",
                link=f"/career-goal/{goal_id}/plan-tracking",
                dedup_key=f"milestone:{goal_id}:{milestone}",
            )
