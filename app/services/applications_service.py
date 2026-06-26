from __future__ import annotations

import sqlite3
from typing import Any

from app.core.security import now_ms
from app.repositories import applications as applications_repo
from app.repositories import mocks as mocks_repo
from app.repositories import reviews as reviews_repo
from app.services import notifications_service

_HOUR_MS = 3600 * 1000

# Partner pipeline thresholds (use-case APP-05): 8h -> 24h -> 48h -> 120h.
_PARTNER_STAGES = [
    (0, "referral_sent"),
    (8 * _HOUR_MS, "under_review"),
    (24 * _HOUR_MS, "interview"),
    (48 * _HOUR_MS, "final_round"),
    (120 * _HOUR_MS, "offer_extended"),
]

_PARTNER_LABEL = {
    "referral_sent": "Referral sent",
    "under_review": "Under review",
    "interview": "Interview stage",
    "final_round": "Final round",
    "offer_extended": "Offer extended",
}


def partner_status_for(submitted_at: int) -> str:
    elapsed = now_ms() - submitted_at
    code = "referral_sent"
    for threshold, stage in _PARTNER_STAGES:
        if elapsed >= threshold:
            code = stage
    return code


def advance_partner(conn: sqlite3.Connection, user_id: str, app: dict[str, Any]) -> None:
    """Recompute a partner application's status and notify on change (APP-05).

    Mutates the passed app dict in place and persists the new status.
    """
    if app["kind"] != "partner":
        return
    new_status = partner_status_for(app["submittedAt"])
    if new_status != app.get("partnerStatus"):
        app["partnerStatus"] = new_status
        applications_repo.set_partner_status(conn, app["id"], new_status)
        notifications_service.push(
            user_id,
            type="job",
            severity="success" if new_status == "offer_extended" else "info",
            title="Application update",
            body=f"{app['title']} at {app['company']}: {_PARTNER_LABEL[new_status]}.",
            link="/applications",
            dedup_key=f"app:{app['id']}:{new_status}",
        )


def with_counts(conn: sqlite3.Connection, user_id: str, app: dict[str, Any]) -> dict[str, Any]:
    review_count = reviews_repo.count_for_app(conn, user_id, app["id"])
    mock_count = mocks_repo.count_for_app(conn, user_id, app["id"])
    return {**app, "reviewCount": review_count, "mockCount": mock_count}


def summarize(apps: list[dict[str, Any]]) -> dict[str, int]:
    partner = sum(1 for a in apps if a["kind"] == "partner")
    self_tracked = sum(1 for a in apps if a["kind"] == "standard")
    offers = sum(
        1
        for a in apps
        if (a["kind"] == "partner" and a.get("partnerStatus") == "offer_extended")
        or (a["kind"] == "standard" and a.get("manualStatus") == "offer")
    )
    in_progress = 0
    for a in apps:
        if a["kind"] == "partner":
            if a.get("partnerStatus") != "offer_extended":
                in_progress += 1
        else:
            if a.get("manualStatus") in ("applied", "screening", "interview"):
                in_progress += 1
    return {
        "total": len(apps),
        "partner": partner,
        "selfTracked": self_tracked,
        "inProgress": in_progress,
        "offers": offers,
    }
