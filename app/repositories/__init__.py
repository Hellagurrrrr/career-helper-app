"""Repository layer: direct, per-row SQL over the normalized SQLite schema.

Each module owns one bounded context and exposes plain functions that take a
``sqlite3.Connection`` as their first argument. Rows are returned as snake_case
dicts; the camelCase API shape is applied once at the Pydantic boundary
(``app.schemas.*`` ``CamelModel``). This is the target pattern that replaces the
``PersistentDict``/full-table-rewrite design in ``app.services.store``.
"""
