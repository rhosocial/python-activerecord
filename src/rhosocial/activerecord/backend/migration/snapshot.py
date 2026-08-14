# src/rhosocial/activerecord/backend/migration/snapshot.py
"""Schema snapshot capture, serialisation, and diff helpers for migration runners.

Both :class:`MigrationRunner` and :class:`AsyncMigrationRunner` share these
helpers. The schema differ is obtained from the dialect via
``dialect.create_schema_differ()`` — the dependency-inversion point that keeps
the core library free of any concrete backend differ imports.
"""

from __future__ import annotations

from typing import Any

from rhosocial.activerecord.backend.schema.differ import SchemaDiffer


def take_sync_snapshot(backend: Any) -> Any | None:
    """Capture a schema snapshot synchronously via the backend's introspector."""
    try:
        introspector = getattr(backend, "introspector", None)
        dialect = getattr(backend, "dialect", None)
        if introspector is None or dialect is None:
            return None
        from rhosocial.activerecord.backend.schema import SyncSchemaSnapshotBuilder

        builder = SyncSchemaSnapshotBuilder(introspector, dialect)
        return builder.build()
    except Exception:
        return None


async def take_async_snapshot(backend: Any) -> Any | None:
    """Capture a schema snapshot asynchronously via the backend's introspector."""
    try:
        introspector = getattr(backend, "introspector", None)
        dialect = getattr(backend, "dialect", None)
        if introspector is None or dialect is None:
            return None
        from rhosocial.activerecord.backend.schema import AsyncSchemaSnapshotBuilder

        builder = AsyncSchemaSnapshotBuilder(introspector, dialect)
        return await builder.build()
    except Exception:
        return None


def snapshot_to_dict(snapshot: Any) -> dict | None:
    """Serialize a ``SchemaSnapshot`` to a plain JSON-safe dict."""
    if snapshot is None:
        return None
    try:
        data = snapshot.to_dict()
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def compute_schema_diff(before: Any, after: Any, dialect: Any) -> Any | None:
    """Compare two ``SchemaSnapshot`` instances using the dialect's differ.

    The differ is resolved through ``dialect.create_schema_differ()`` so the
    core never imports concrete backend differ implementations. If the dialect
    provides none, the generic :class:`SchemaDiffer` is used as a fallback.
    """
    if before is None or after is None:
        return None
    try:
        if dialect is not None and hasattr(dialect, "create_schema_differ"):
            differ = dialect.create_schema_differ()
        else:
            differ = SchemaDiffer()
        return differ.compare(before, after)
    except Exception:
        return None
