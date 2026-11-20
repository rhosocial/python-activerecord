# src/rhosocial/activerecord/migration/runner.py
"""ActiveRecord-layer migration runner: order, execute, preview, record.

Owns the management semantics the user's up/down logic does not:
- caller-defined order (UP as given, DOWN reversed);
- dependency validation (must be earlier in the group or already applied);
- duplicate / conflict guards;
- dry-run (render every statement, apply nothing);
- version records via a pluggable store.

Does not use the backend migration runtime system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Sequence, TYPE_CHECKING

from .context import AsyncMigrationContext, MigrationContext
from .core import AsyncMigration, Migration
from .record import InMemoryMigrationRecordStore, MigrationRecord, MigrationRecordStore

if TYPE_CHECKING:  # pragma: no cover
    from ..backend.base import StorageBackend


class MigrationError(Exception):
    pass


class MigrationDependencyError(MigrationError):
    pass


class MigrationAlreadyAppliedError(MigrationError):
    pass


class MigrationNotAppliedError(MigrationError):
    pass


@dataclass
class MigrationResult:
    version: str
    direction: str
    dry_run: bool
    statements: int
    dry_run_sql: List[tuple] = field(default_factory=list)


@dataclass
class MigrationGroupResult:
    direction: str
    dry_run: bool
    versions: List[str]
    applied: List[str]
    rolled_back: List[str]
    results: List[MigrationResult] = field(default_factory=list)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class _RunnerBase:
    def _validate(
        self, migrations: Sequence[Migration], direction: str, store: MigrationRecordStore
    ) -> List[Migration]:
        seen = set()
        for m in migrations:
            if m.version in seen:
                raise MigrationError(f"duplicate migration version {m.version!r}")
            seen.add(m.version)
        applied = set(store.get_applied())
        for i, m in enumerate(migrations):
            if direction == "up":
                if m.version in applied:
                    raise MigrationAlreadyAppliedError(m.version)
                earlier = {x.version for x in migrations[:i]} | applied
                for dep in m.dependencies:
                    if dep not in earlier:
                        raise MigrationDependencyError(
                            f"{m.version} depends on {dep!r}, which is neither earlier nor applied"
                        )
            else:
                if m.version not in applied:
                    raise MigrationNotAppliedError(m.version)
        return list(reversed(list(migrations))) if direction == "down" else list(migrations)


class MigrationRunner(_RunnerBase):
    def __init__(self, backend: "StorageBackend"):
        self.backend = backend

    def run(
        self,
        migrations: Sequence[Migration],
        *,
        direction: str = "up",
        store: Optional[MigrationRecordStore] = None,
        dry_run: bool = False,
    ) -> MigrationGroupResult:
        store = store or InMemoryMigrationRecordStore()
        ordered = self._validate(migrations, direction, store)
        versions = [m.version for m in ordered]
        results: List[MigrationResult] = []
        applied: List[str] = []
        rolled_back: List[str] = []
        for m in ordered:
            ctx = MigrationContext(
                self.backend, direction=direction, version=m.version, dry_run=dry_run
            )
            fn = m.up if direction == "up" else m.down
            fn(ctx)
            results.append(
                MigrationResult(
                    m.version, direction, dry_run, len(ctx.dry_run_sql), list(ctx.dry_run_sql)
                )
            )
            if dry_run:
                continue
            store.record(MigrationRecord(m.version, direction, _utcnow(), True))
            (applied if direction == "up" else rolled_back).append(m.version)
        return MigrationGroupResult(direction, dry_run, versions, applied, rolled_back, results)


class AsyncMigrationRunner(_RunnerBase):
    def __init__(self, backend: "StorageBackend"):
        self.backend = backend

    async def run(
        self,
        migrations: Sequence[AsyncMigration],
        *,
        direction: str = "up",
        store: Optional[MigrationRecordStore] = None,
        dry_run: bool = False,
    ) -> MigrationGroupResult:
        store = store or InMemoryMigrationRecordStore()
        ordered = self._validate(migrations, direction, store)
        versions = [m.version for m in ordered]
        results: List[MigrationResult] = []
        applied: List[str] = []
        rolled_back: List[str] = []
        for m in ordered:
            ctx = AsyncMigrationContext(
                self.backend, direction=direction, version=m.version, dry_run=dry_run
            )
            fn = m.up if direction == "up" else m.down
            await fn(ctx)
            results.append(
                MigrationResult(
                    m.version, direction, dry_run, len(ctx.dry_run_sql), list(ctx.dry_run_sql)
                )
            )
            if dry_run:
                continue
            store.record(MigrationRecord(m.version, direction, _utcnow(), True))
            (applied if direction == "up" else rolled_back).append(m.version)
        return MigrationGroupResult(direction, dry_run, versions, applied, rolled_back, results)
