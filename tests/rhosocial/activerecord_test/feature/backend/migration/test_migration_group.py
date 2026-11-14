# tests/rhosocial/activerecord_test/feature/backend/migration/test_migration_group.py
"""Shared migration group runner: ordering, records, dry-run, CLI."""

import json
try:  # Python 3.8 has no typing.Annotated
    from typing import Annotated, Optional
except ImportError:  # pragma: no cover - only on 3.8
    from typing import Optional

    from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import (
    AsyncSQLiteBackend,
)
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.migration import (
    JSONFileMigrationRecordStore,
    MigrationDependencyError,
    MigrationDirection,
    MigrationError,
    MigrationFunctionExecutionError,
    MigrationVersionConflictError,
    migration,
    run_migration_group,
    run_migration_group_async,
    select_async_functions,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.base import (
    IdentityAttribute,
    UseColumnAttributes,
    UseSqlType,
)
from rhosocial.activerecord.cli import main
from rhosocial.activerecord.model import ActiveRecord


class GroupUser(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "mig_group_users"

    id: Annotated[
        Optional[int],
        UseSqlType(IntegerType()),
        UseColumnAttributes(IdentityAttribute()),
    ] = None
    name: Annotated[str, UseSqlType(VarCharType(length=64))]


class GroupPost(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "mig_group_posts"

    id: Annotated[
        Optional[int],
        UseSqlType(IntegerType()),
        UseColumnAttributes(IdentityAttribute()),
    ] = None
    title: Annotated[str, UseSqlType(VarCharType(length=64))]


class GroupDirect(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "mig_group_direct"

    id: Annotated[
        Optional[int],
        UseSqlType(IntegerType()),
        UseColumnAttributes(IdentityAttribute()),
    ] = None
    name: Annotated[str, UseSqlType(VarCharType(length=64))]


class GroupPair(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "mig_group_pairs"

    id: Annotated[
        Optional[int],
        UseSqlType(IntegerType()),
        UseColumnAttributes(IdentityAttribute()),
    ] = None
    name: Annotated[str, UseSqlType(VarCharType(length=64))]


@migration("g001_create_users")
def create_users(ctx):
    if ctx.direction == MigrationDirection.UP:
        ctx.apply(GroupUser.create_table_statement(backend=ctx.backend))
    else:
        ctx.apply(GroupUser.drop_table_statement(backend=ctx.backend, if_exists=True))


@migration("g002_create_posts", dependencies=("g001_create_users",))
def create_posts(ctx):
    if ctx.direction == MigrationDirection.UP:
        ctx.apply(GroupPost.create_table_statement(backend=ctx.backend))
    else:
        ctx.apply(GroupPost.drop_table_statement(backend=ctx.backend, if_exists=True))


@migration("g003_direct_write")
def direct_write(ctx):
    if ctx.direction == MigrationDirection.UP:
        GroupDirect.create_table(backend=ctx.backend)
    else:
        GroupDirect.drop_table(backend=ctx.backend, if_exists=True)


@migration("g004_failure")
def failing_migration(ctx):
    raise ValueError("boom")


@migration("g005_failure_after_create", dependencies=("g001_create_users",))
def failing_after_create(ctx):
    raise RuntimeError("later boom")


PAIR_VERSION = "g006_pair"


@migration(PAIR_VERSION, async_variant=f"{__name__}:async_create_pair")
def create_pair(ctx):
    if ctx.direction == MigrationDirection.UP:
        ctx.apply(GroupPair.create_table_statement(backend=ctx.backend))
    else:
        ctx.apply(GroupPair.drop_table_statement(backend=ctx.backend, if_exists=True))


@migration(PAIR_VERSION)
async def async_create_pair(ctx):
    if ctx.direction == MigrationDirection.UP:
        await ctx.apply(GroupPair.create_table_statement(backend=ctx.backend))
    else:
        await ctx.apply(GroupPair.drop_table_statement(backend=ctx.backend, if_exists=True))


def _backend(path=":memory:"):
    backend = SQLiteBackend(SQLiteConnectionConfig(database=str(path)))
    backend.connect()
    return backend


def _tables(backend):
    rows = (
        backend.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True),
        ).data
        or []
    )
    return {row["name"] for row in rows if not row["name"].startswith("sqlite_")}


def _fqn(name: str) -> str:
    return f"{__name__}:{name}"


def test_group_runs_up_in_order_and_down_in_reverse(tmp_path):
    backend = _backend()
    try:
        result = run_migration_group(backend, [create_users, create_posts])
        assert result.versions == ["g001_create_users", "g002_create_posts"]
        assert result.applied == result.versions
        assert _tables(backend) == {"mig_group_users", "mig_group_posts"}

        result = run_migration_group(
            backend, [create_users, create_posts], direction=MigrationDirection.DOWN
        )
        assert result.versions == ["g002_create_posts", "g001_create_users"]
        assert result.rolled_back == result.versions
        assert _tables(backend) == set()
    finally:
        backend.disconnect()


def test_group_writes_records_only_after_success(tmp_path):
    backend = _backend()
    store = JSONFileMigrationRecordStore(tmp_path / "records.json")
    try:
        result = run_migration_group(backend, [create_users, create_posts], record_store=store)
        assert result.records_written == ["g001_create_users", "g002_create_posts"]
        assert [record.version for record in store.get_applied()] == result.versions

        with pytest.raises(MigrationFunctionExecutionError) as caught:
            run_migration_group(backend, [failing_migration], record_store=store)
        assert caught.value.version == "g004_failure"
        assert caught.value.fqn == _fqn("failing_migration")
        assert isinstance(caught.value.cause, ValueError)
        assert [record.version for record in store.get_applied()] == result.versions
    finally:
        backend.disconnect()


def test_group_validates_dependencies_and_duplicates():
    backend = _backend()
    try:
        with pytest.raises(MigrationDependencyError, match="g001_create_users"):
            run_migration_group(backend, [create_posts])
        with pytest.raises(Exception, match="Duplicate migration version"):
            run_migration_group(backend, [create_users, create_users])
    finally:
        backend.disconnect()


def test_group_rejects_a_version_owned_by_another_fqn(tmp_path):
    backend = _backend()
    store = JSONFileMigrationRecordStore(tmp_path / "records.json")
    from datetime import datetime, timezone

    from rhosocial.activerecord.backend.migration import MigrationRecord

    store.record(
        MigrationRecord(
            version="g001_create_users",
            migration_fqn="other.module:other_function",
            direction="up",
            applied_at=datetime.now(timezone.utc),
            success=True,
        )
    )
    try:
        with pytest.raises(MigrationVersionConflictError):
            run_migration_group(backend, [create_users], record_store=store)
    finally:
        backend.disconnect()


def test_dry_run_blocks_direct_mixin_writes():
    backend = _backend()
    try:
        result = run_migration_group(backend, [direct_write], dry_run=True)
        assert result.dry_run is True
        assert result.dry_run_total == 1
        assert "CREATE TABLE" in result.dry_run_sql[0][1].upper()
        assert _tables(backend) == set()
    finally:
        backend.disconnect()


def test_dry_run_records_ctx_apply_and_does_not_duplicate():
    backend = _backend()
    try:
        result = run_migration_group(backend, [create_users], dry_run=True)
        assert result.dry_run_total == 1
        assert len(result.dry_run_sql) == 1
        assert result.dry_run_sql[0][0].startswith("g001_create_users")
        assert _tables(backend) == set()
    finally:
        backend.disconnect()


def test_cli_migrate_without_model_uses_explicit_backend(tmp_path):
    database = tmp_path / "group.sqlite"
    records = tmp_path / "records.json"
    common = [
        "migrate",
        _fqn("create_users"),
        _fqn("create_posts"),
        "--backend-class",
        "rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend",
        "--config-class",
        "rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig",
        "--config",
        f"database={database}",
        "--record-store",
        str(records),
    ]

    assert main(common) == 0
    backend = _backend(database)
    try:
        assert _tables(backend) == {"mig_group_users", "mig_group_posts"}
    finally:
        backend.disconnect()

    assert main(common + ["--direction", "down"]) == 0
    backend = _backend(database)
    try:
        assert _tables(backend) == set()
    finally:
        backend.disconnect()


def test_cli_migrate_without_model_requires_explicit_backend():
    assert main(["migrate", _fqn("create_users")]) != 0


def test_cli_usage_error_exits_with_usage_code(capsys):
    code = main(["migrate", _fqn("create_users")])
    assert code == 2
    assert "Module-level migration functions" in capsys.readouterr().err


def test_cli_dependency_error_exits_with_state_code(capsys, tmp_path):
    database = tmp_path / "state.sqlite"
    code = main(
        [
            "migrate",
            _fqn("create_posts"),
            "--backend-class",
            "rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend",
            "--config-class",
            "rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig",
            "--config",
            f"database={database}",
        ]
    )
    assert code == 7
    assert "depends on" in capsys.readouterr().err


def test_cli_function_failure_exits_with_failure_code(capsys, tmp_path):
    database = tmp_path / "failure.sqlite"
    code = main(
        [
            "migrate",
            _fqn("failing_migration"),
            "--backend-class",
            "rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend",
            "--config-class",
            "rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig",
            "--config",
            f"database={database}",
        ]
    )
    assert code == 8
    err = capsys.readouterr().err
    assert "g004_failure" in err
    assert "boom" in err


def test_cli_json_success_and_dry_run(capsys, tmp_path):
    database = tmp_path / "json.sqlite"
    common = [
        "migrate",
        _fqn("create_users"),
        _fqn("create_posts"),
        "--backend-class",
        "rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend",
        "--config-class",
        "rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig",
        "--config",
        f"database={database}",
        "--output",
        "json",
    ]
    assert main(common) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] is True
    assert payload["applied"] == ["g001_create_users", "g002_create_posts"]
    assert payload["direction"] == "up"

    assert main(common + ["--dry-run"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert payload["dry_run_total"] == 2
    assert payload["statements"][0]["label"].startswith("g001_create_users")


def test_cli_json_failure_reports_executed_versions(capsys, tmp_path):
    database = tmp_path / "json_failure.sqlite"
    code = main(
        [
            "migrate",
            _fqn("create_users"),
            _fqn("failing_after_create"),
            "--backend-class",
            "rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend",
            "--config-class",
            "rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig",
            "--config",
            f"database={database}",
            "--output",
            "json",
        ]
    )
    assert code == 8
    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] is False
    assert payload["exit_code"] == 8
    assert payload["migration_version"] == "g005_failure_after_create"
    assert payload["executed"] == ["g001_create_users"]
    assert payload["transactional_ddl"] is True
    assert payload["rolled_back"] is True


def test_cli_json_list_and_plan(capsys):
    common = [
        "migrate",
        _fqn("create_users"),
        _fqn("create_posts"),
        "--output",
        "json",
    ]
    assert main(common + ["--list"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "list"
    assert payload["functions"][1]["dependencies"] == ["g001_create_users"]

    assert main(common + ["--plan", "--direction", "down"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "plan"
    assert payload["direction"] == "down"
    assert payload["order"][0]["version"] == "g002_create_posts"


def test_cli_list_and_plan_stop_before_connecting(capsys):
    code = main(
        [
            "migrate",
            _fqn("create_users"),
            _fqn("create_posts"),
            "--list",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "g001_create_users" in out
    assert "g002_create_posts" in out
    assert "dependencies: g001_create_users" in out

    code = main(
        [
            "migrate",
            _fqn("create_users"),
            _fqn("create_posts"),
            "--plan",
            "--direction",
            "down",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert lines[0] == "Execution order (down):"
    assert lines[1].lstrip().startswith("g002_create_posts")
    assert lines[2].lstrip().startswith("g001_create_users")


def test_select_async_functions_keeps_the_sync_fqn():
    selected = select_async_functions([create_pair])
    assert len(selected) == 1
    assert selected[0].fqn == _fqn("create_pair")
    assert selected[0].is_async is True
    assert selected[0].function.__name__ == "async_create_pair"

    with pytest.raises(MigrationError, match="async_variant"):
        select_async_functions([create_users])


async def test_async_runner_uses_the_paired_function_and_records_sync_fqn(tmp_path):
    backend = AsyncSQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
    await backend.connect()
    store = JSONFileMigrationRecordStore(tmp_path / "paired.json")
    try:
        result = await run_migration_group_async(backend, [create_pair], record_store=store)
        assert result.versions == [PAIR_VERSION]
        assert await backend.introspector.table_exists("mig_group_pairs")
        records = store.get_applied()
        assert records[0].migration_fqn == _fqn("create_pair")
    finally:
        await backend.disconnect()


def test_cli_async_uses_the_paired_variant(tmp_path):
    database = tmp_path / "paired.sqlite"
    assert (
        main(
            [
                "migrate",
                _fqn("create_pair"),
                "--async",
                "--backend-class",
                "rhosocial.activerecord.backend.impl.sqlite.backend.async_backend:AsyncSQLiteBackend",
                "--config-class",
                "rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig",
                "--config",
                f"database={database}",
            ]
        )
        == 0
    )
