from __future__ import annotations

from typing import Any

from app.core.security import now_ms
from app.services import notifications_service
from app.services.store import store

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


def advance_partner(user_id: str, app: dict[str, Any]) -> None:
    """Recompute a partner application's status and notify on change (APP-05)."""
    if app["kind"] != "partner":
        return
    new_status = partner_status_for(app["submittedAt"])
    if new_status != app.get("partnerStatus"):
        app["partnerStatus"] = new_status
        notifications_service.push(
            user_id,
            type="job",
            severity="success" if new_status == "offer_extended" else "info",
            title="Application update",
            body=f"{app['title']} at {app['company']}: {_PARTNER_LABEL[new_status]}.",
            link="/applications",
            dedup_key=f"app:{app['id']}:{new_status}",
        )


def with_counts(user_id: str, app: dict[str, Any]) -> dict[str, Any]:
    reviews = store.reviews.get(user_id, {}).get(app["id"], [])
    mocks = store.mocks.get(user_id, {}).get(app["id"], [])
    return {**app, "reviewCount": len(reviews), "mockCount": len(mocks)}


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
