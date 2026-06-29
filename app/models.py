"""Shared domain models (framework-agnostic, no persistence concerns)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UserRecord:
    id: str
    email: str
    name: str
    password_hash: str
    created_at: int
