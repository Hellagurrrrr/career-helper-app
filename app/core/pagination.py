from __future__ import annotations

import base64
import json
from typing import Any

from app.core.errors import validation_error


def _encode_cursor(offset: int) -> str:
    raw = json.dumps({"o": offset}).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str) -> int:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        return int(json.loads(raw)["o"])
    except Exception:
        raise validation_error("Invalid cursor.", "cursor")


def paginate(items: list[Any], limit: int, cursor: str | None) -> dict[str, Any]:
    """Offset-based cursor pagination matching the api-design 1.4 envelope."""
    offset = _decode_cursor(cursor) if cursor else 0
    page = items[offset : offset + limit]
    next_offset = offset + limit
    next_cursor = _encode_cursor(next_offset) if next_offset < len(items) else None
    return {"items": page, "nextCursor": next_cursor, "total": len(items)}
