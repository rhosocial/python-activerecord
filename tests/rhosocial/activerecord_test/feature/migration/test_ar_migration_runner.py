# tests/rhosocial/activerecord_test/feature/migration/test_ar_migration_runner.py
"""Contracts for the ActiveRecord-layer migration runner and context.

Verifies the closed loop: a user's up/down logic calls ctx.apply(...) with
expressions, dry-run renders without executing, a real run executes and records,
DOWN reverses + clears, and backend suggestions are reachable from the context.
No backend migration runtime system is involved.
"""

import pytest

from rhosocial.activerecord.migration import (
    Migration,
    AsyncMigration,
    MigrationContext,
    AsyncMigrationContext,
    MigrationRunner,
    AsyncMigrationRunner,
    InMemoryMigrationRecordStore,
    MigrationError,
    MigrationAlreadyAppliedError,
    MigrationDependencyError,
    MigrationNotAppliedError,
)
from rhosocial.activerecord.backend.expression.statements import PartitionStrategy


class FakeExpr:
    """Minimal expression node (to_sql only)."""

    def __init__(self, sql):
        self.sql = sql

    def to_sql(self):
        return self.sql, ()


class FakeBackend:
    """Records executed SQL without a real database."""

    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None, options=None):
        self.executed.append((sql, params, options))


def _migration(version, up_sql, down_sql, deps=()):
    def up(ctx):
        ctx.apply([FakeExpr(s) for s in up_sql])

    def down(ctx):
        ctx.apply([FakeExpr(s) for s in down_sql])

    return Migration(version, up, down, tuple(deps))


def test_context_apply_dry_run_renders_without_executing():
    backend = FakeBackend()
    ctx = MigrationContext(backend, dry_run=True, version="v1")
    n = ctx.apply(FakeExpr("CREATE TABLE a"), FakeExpr("CREATE TABLE b"))
    assert n == 2
    assert [sql for sql, _ in ctx.dry_run_sql] == ["CREATE TABLE a", "CREATE TABLE b"]
    assert backend.executed == []


def test_context_apply_real_executes():
    backend = FakeBackend()
    ctx = MigrationContext(backend)
    n = ctx.apply(FakeExpr("ALTER TABLE a ADD COLUMN x INT"))
    assert n == 1
    assert backend.executed[0][0] == "ALTER TABLE a ADD COLUMN x INT"
    assert ctx.dry_run_sql == []


def test_context_exposes_eight_partition_suggestions():
    ctx = MigrationContext(FakeBackend())
    names = [n for n in dir(ctx) if n.startswith("suggest_partition_")]
    assert len(names) == 8
    # SQLite has no partitioning -> suggestion returns None (structural/no-op)
    assert ctx.suggest_partition_add(PartitionStrategy.RANGE, None) is None
    assert ctx.apply(ctx.suggest_partition_add(PartitionStrategy.RANGE, None)) == 0


def test_runner_up_records_and_down_reverses_and_clears():
    backend = FakeBackend()
    runner = MigrationRunner(backend)
    store = InMemoryMigrationRecordStore()
    migs = [_migration("v1", ["UP1"], ["DOWN1"]), _migration("v2", ["UP2"], ["DOWN2"])]

    up = runner.run(migs, store=store)
    assert up.versions == ["v1", "v2"]
    assert up.applied == ["v1", "v2"]
    assert store.get_applied() == ["v1", "v2"]
    assert [s for s, _, _ in backend.executed] == ["UP1", "UP2"]

    # runner reverses DOWN itself; pass the original (UP) order
    down = runner.run(migs, direction="down", store=store)
    assert down.versions == ["v2", "v1"]
    assert down.rolled_back == ["v2", "v1"]
    assert store.get_applied() == []


def test_runner_dry_run_applies_nothing_and_no_records():
    backend = FakeBackend()
    runner = MigrationRunner(backend)
    store = InMemoryMigrationRecordStore()
    result = runner.run([_migration("v1", ["UP1"], ["DOWN1"])], store=store, dry_run=True)
    assert result.dry_run is True
    assert backend.executed == []
    assert store.get_applied() == []
    assert result.results[0].dry_run_sql == [("UP1", ())]


def test_runner_dependency_and_duplicate_guards():
    backend = FakeBackend()
    runner = MigrationRunner(backend)
    with pytest.raises(MigrationDependencyError):
        runner.run([_migration("v2", ["UP2"], ["DOWN2"], deps=("v1",))])
    with pytest.raises(MigrationError):
        runner.run([_migration("v1", ["UP1"], ["D1"]), _migration("v1", ["UP1"], ["D1"])])


def test_runner_guards_on_unapplied_down():
    backend = FakeBackend()
    runner = MigrationRunner(backend)
    with pytest.raises(MigrationNotAppliedError):
        runner.run([_migration("v9", ["UP9"], ["DOWN9"])], direction="down")


def test_runner_guards_on_already_applied():
    backend = FakeBackend()
    runner = MigrationRunner(backend)
    store = InMemoryMigrationRecordStore()
    runner.run([_migration("v1", ["UP1"], ["D1"])], store=store)
    with pytest.raises(MigrationAlreadyAppliedError):
        runner.run([_migration("v1", ["UP1"], ["D1"])], store=store)


class AsyncFakeBackend:
    def __init__(self):
        self.executed = []

    async def execute(self, sql, params=None, options=None):
        self.executed.append((sql, params, options))


@pytest.mark.asyncio
async def test_async_runner_parity_with_sync():
    """AsyncMigrationRunner mirrors sync: up records, down reverses + clears."""
    backend = AsyncFakeBackend()
    runner = AsyncMigrationRunner(backend)

    async def up1(ctx):
        await ctx.apply([FakeExpr("UP1")])

    async def down1(ctx):
        await ctx.apply([FakeExpr("DOWN1")])

    async def up2(ctx):
        await ctx.apply([FakeExpr("UP2")])

    async def down2(ctx):
        await ctx.apply([FakeExpr("DOWN2")])

    migs = [AsyncMigration("v1", up1, down1), AsyncMigration("v2", up2, down2)]
    store = InMemoryMigrationRecordStore()
    up = await runner.run(migs, store=store)
    assert up.applied == ["v1", "v2"]
    assert [s for s, _, _ in backend.executed] == ["UP1", "UP2"]
    down = await runner.run(migs, direction="down", store=store)
    assert down.rolled_back == ["v2", "v1"]
    assert store.get_applied() == []


@pytest.mark.asyncio
async def test_async_context_dry_run_renders_without_executing():
    backend = AsyncFakeBackend()
    ctx = AsyncMigrationContext(backend, dry_run=True, version="v1")
    n = await ctx.apply(FakeExpr("CREATE TABLE a"))
    assert n == 1
    assert ctx.dry_run_sql == [("CREATE TABLE a", ())]
    assert backend.executed == []
