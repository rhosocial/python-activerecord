# src/rhosocial/activerecord/migration/core.py
"""A user-declared migration: a versioned ``up``/``down`` pair.

Both up and down take a single ``ctx`` (the MigrationContext). This is the
user-facing spec; the runner owns ordering, execution, dry-run and records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence, TYPE_CHECKING

#: The default migration direction; shared by context and runner defaults.
DEFAULT_DIRECTION = "up"

if TYPE_CHECKING:  # pragma: no cover
    from .context import AsyncMigrationContext, MigrationContext


@dataclass(frozen=True)
class Migration:
    """A synchronous migration declaration."""

    version: str
    up: Callable[["MigrationContext"], None]
    down: Callable[["MigrationContext"], None]
    dependencies: Sequence[str] = field(default_factory=tuple)
    description: str = ""


@dataclass(frozen=True)
class AsyncMigration:
    """An asynchronous migration declaration (parity with Migration)."""

    version: str
    up: Callable[["AsyncMigrationContext"], object]
    down: Callable[["AsyncMigrationContext"], object]
    dependencies: Sequence[str] = field(default_factory=tuple)
    description: str = ""
