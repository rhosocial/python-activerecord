# tests/rhosocial/activerecord_test/feature/backend/ddl/test_migration_async.py
"""
Async twin of test_migration.py.

Pure-sync surface (direction enum, record stores, resolvers, batch runner
bookkeeping) lives on sync classes and needs no async exercise; the async
twin covers the I/O-bearing integration paths of AsyncMigrationRunner.
"""

import pytest

from rhosocial.activerecord.backend.migration.core import AsyncNamedMigration
from rhosocial.activerecord.backend.migration.runner import MigrationDirection

from tests.rhosocial.activerecord_test.feature.backend.ddl.test_migration import (
    register_temp_module,
    unregister_temp_module,
    _make_create_users_expr_static,
    _make_drop_users_expr_static,
)


class TestAsyncMigrationRunnerIntegrationAsync:
    """Async integration twin covering AsyncMigrationRunner I/O paths."""

    @pytest.fixture(autouse=True)
    def _cleanup(self, request):
        self._temp_modules = []
        yield
        for name in self._temp_modules:
            unregister_temp_module(name)
        self._temp_modules.clear()

    def _register(self, name, functions):
        mod = register_temp_module(name, functions)
        self._temp_modules.append(name)
        return mod

    @pytest.mark.asyncio
    async def test_async_up_creates_table(self):
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
        from rhosocial.activerecord.backend.migration.async_runner import AsyncMigrationRunner

        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        try:
            self._register("async_mig_test.expressions", {
                "create_users_table": lambda dialect: _make_create_users_expr_static(dialect),
                "drop_users_table": lambda dialect: _make_drop_users_expr_static(dialect),
            })

            class V001CreateUsers(AsyncNamedMigration):
                version = "v001_create_users"
                async def run(self, ctx):
                    if ctx.direction == MigrationDirection.UP:
                        await ctx.execute("async_mig_test.expressions.create_users_table")
                    else:
                        await ctx.execute("async_mig_test.expressions.drop_users_table")

            self._register("async_mig_test.migrations", {"V001CreateUsers": V001CreateUsers})

            runner = AsyncMigrationRunner("async_mig_test.migrations.V001CreateUsers")
            result = await runner.run(backend, MigrationDirection.UP)

            assert result.success is True
            assert result.version == "v001_create_users"
            cursor = await backend._get_cursor()
            await cursor.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
            )
            row = await cursor.fetchone()
            assert row[0] == 1
            await cursor.close()
        finally:
            await backend.disconnect()

    @pytest.mark.asyncio
    async def test_async_up_then_down(self):
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
        from rhosocial.activerecord.backend.migration.async_runner import AsyncMigrationRunner

        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        try:
            self._register("async_mig_test2.expressions", {
                "create_users_table": lambda dialect: _make_create_users_expr_static(dialect),
                "drop_users_table": lambda dialect: _make_drop_users_expr_static(dialect),
            })

            class V001CreateUsers(AsyncNamedMigration):
                version = "v001_create_users"
                async def run(self, ctx):
                    if ctx.direction == MigrationDirection.UP:
                        await ctx.execute("async_mig_test2.expressions.create_users_table")
                    else:
                        await ctx.execute("async_mig_test2.expressions.drop_users_table")

            self._register("async_mig_test2.migrations", {"V001CreateUsers": V001CreateUsers})

            runner = AsyncMigrationRunner("async_mig_test2.migrations.V001CreateUsers")

            up_result = await runner.run(backend, MigrationDirection.UP)
            assert up_result.success is True

            cursor = await backend._get_cursor()
            await cursor.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
            )
            assert (await cursor.fetchone())[0] == 1
            await cursor.close()

            down_result = await runner.run(backend, MigrationDirection.DOWN)
            assert down_result.success is True

            cursor = await backend._get_cursor()
            await cursor.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
            )
            assert (await cursor.fetchone())[0] == 0
            await cursor.close()
        finally:
            await backend.disconnect()

    @pytest.mark.asyncio
    async def test_async_dry_run_skips_execution(self):
        """dry_run=True runs the migration but skips backend.execute()."""
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
        from rhosocial.activerecord.backend.migration.async_runner import AsyncMigrationRunner

        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        try:
            self._register("async_mig_test3.expressions", {
                "create_users_table": lambda dialect: _make_create_users_expr_static(dialect),
            })

            class V001DryRun(AsyncNamedMigration):
                version = "v001_dry_run"
                async def run(self, ctx):
                    await ctx.execute("async_mig_test3.expressions.create_users_table")

            self._register("async_mig_test3.migrations", {"V001DryRun": V001DryRun})

            runner = AsyncMigrationRunner("async_mig_test3.migrations.V001DryRun")
            result = await runner.run(backend, MigrationDirection.UP, dry_run=True)

            assert result.success is True
            cursor = await backend._get_cursor()
            await cursor.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
            )
            # dry_run must NOT have created the table
            assert (await cursor.fetchone())[0] == 0
            await cursor.close()
        finally:
            await backend.disconnect()

    @pytest.mark.asyncio
    async def test_async_record_store(self, tmp_path):
        """record_store records UP and DOWN runs."""
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
        from rhosocial.activerecord.backend.migration.async_runner import AsyncMigrationRunner
        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore

        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        try:
            self._register("async_mig_test4.expressions", {
                "create_users_table": lambda dialect: _make_create_users_expr_static(dialect),
                "drop_users_table": lambda dialect: _make_drop_users_expr_static(dialect),
            })

            class V001Recorded(AsyncNamedMigration):
                version = "v001_recorded"
                async def run(self, ctx):
                    if ctx.direction == MigrationDirection.UP:
                        await ctx.execute("async_mig_test4.expressions.create_users_table")
                    else:
                        await ctx.execute("async_mig_test4.expressions.drop_users_table")

            self._register("async_mig_test4.migrations", {"V001Recorded": V001Recorded})

            store = JSONFileMigrationRecordStore(tmp_path / "async_records.json")
            runner = AsyncMigrationRunner("async_mig_test4.migrations.V001Recorded")

            await runner.run(backend, MigrationDirection.UP, record_store=store)
            assert store.is_applied("v001_recorded") is True

            await runner.run(backend, MigrationDirection.DOWN, record_store=store)
            assert store.is_applied("v001_recorded") is False
        finally:
            await backend.disconnect()
