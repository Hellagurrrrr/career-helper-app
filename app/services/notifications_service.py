from __future__ import annotations

from typing import Any

from app.core.security import new_id, now_ms
from app.services.store import store

MAX_NOTIFICATIONS = 50  # api-design 11.2: keep most recent 50 per user


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

    Returns the created notification, or None if it was a duplicate.
    """
    bucket = store.notifications.setdefault(user_id, [])
    if dedup_key and any(n.get("dedupKey") == dedup_key for n in bucket):
        return None

    notification = {
        "id": new_id("n"),
        "type": type,
        "severity": severity,
        "title": title,
        "body": body,
        "link": link,
        "createdAt": now_ms(),
        "read": False,
        "dedupKey": dedup_key,
    }
    bucket.insert(0, notification)
    del bucket[MAX_NOTIFICATIONS:]
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


def check_milestone(user_id: str, goal_id: str, old_progress: int, new_progress: int, goal_title: str) -> None:
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
