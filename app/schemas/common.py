from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model: accepts snake_case in code, serializes camelCase JSON.

    Matches the camelCase field names used throughout design-docs/api-design.md
    (e.g. accessToken, createdAt, submittedAt).
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
