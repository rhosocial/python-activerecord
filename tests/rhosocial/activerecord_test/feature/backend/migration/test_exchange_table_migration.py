# tests/rhosocial/activerecord_test/feature/backend/migration/test_exchange_table_migration.py
"""A migration that swaps a table with a rebuilt successor table."""

try:  # Python 3.8 has no typing.Annotated
    from typing import Annotated, Optional
except ImportError:  # pragma: no cover - only on 3.8
    from typing import Optional

    from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    AlterTableStatement,
    RenameTableAction,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.migration import (
    JSONFileMigrationRecordStore,
    MigrationDirection,
    migration,
    run_migration_group,
)
from rhosocial.activerecord.base import (
    IdentityAttribute,
    UseColumnAttributes,
    UseSqlType,
)
from rhosocial.activerecord.base.derivation import build_create_table_statement
from rhosocial.activerecord.model import ActiveRecord


class ExchangeLegacy(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "exchange_probe"

    id: Annotated[
        Optional[int],
        UseSqlType(IntegerType()),
        UseColumnAttributes(IdentityAttribute()),
    ] = None
    legacy_value: Annotated[str, UseSqlType(VarCharType(length=64))]


class ExchangeNext(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "exchange_probe_next"

    id: Annotated[
        Optional[int],
        UseSqlType(IntegerType()),
        UseColumnAttributes(IdentityAttribute()),
    ] = None
    value: Annotated[str, UseSqlType(VarCharType(length=64))]
    note: Annotated[Optional[str], UseSqlType(VarCharType(length=128))] = None


@migration("x001_create_exchange_probe")
def create_exchange_probe(ctx):
    if ctx.direction == MigrationDirection.UP:
        ctx.apply(build_create_table_statement(ExchangeLegacy, ctx.backend.dialect))
    else:
        ctx.apply(ExchangeLegacy.drop_table_statement(backend=ctx.backend, if_exists=True))


@migration(
    "x002_swap_exchange_probe",
    dependencies=("x001_create_exchange_probe",),
)
def swap_exchange_probe(ctx):
    """Build the successor, swap names, then retire the old table."""
    dialect = ctx.backend.dialect
    if ctx.direction == MigrationDirection.UP:
        ctx.apply(
            build_create_table_statement(ExchangeNext, dialect),
            AlterTableStatement(
                dialect,
                Table(dialect, "exchange_probe"),
                [RenameTableAction(dialect, "exchange_probe", "exchange_probe_old")],
            ),
            AlterTableStatement(
                dialect,
                Table(dialect, "exchange_probe_next"),
                [RenameTableAction(dialect, "exchange_probe_next", "exchange_probe")],
            ),
        )
    else:
        ctx.apply(
            AlterTableStatement(
                dialect,
                Table(dialect, "exchange_probe"),
                [RenameTableAction(dialect, "exchange_probe", "exchange_probe_next")],
            ),
            AlterTableStatement(
                dialect,
                Table(dialect, "exchange_probe_old"),
                [RenameTableAction(dialect, "exchange_probe_old", "exchange_probe")],
            ),
            ExchangeNext.drop_table_statement(backend=ctx.backend, if_exists=True),
        )


@pytest.fixture
def probe_backend():
    backend = SQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
    backend.connect()
    try:
        yield backend
    finally:
        backend.disconnect()


def _column_exists(backend, table: str, column: str) -> bool:
    return any(info.name == column for info in backend.introspector.list_columns(table))


def _table_exists(backend, table: str) -> bool:
    return backend.introspector.table_exists(table)


def test_exchange_migration_swaps_tables(probe_backend, tmp_path):
    store = JSONFileMigrationRecordStore(tmp_path / "exchange.json")

    result = run_migration_group(
        probe_backend,
        [create_exchange_probe, swap_exchange_probe],
        record_store=store,
    )
    assert result.versions == [
        "x001_create_exchange_probe",
        "x002_swap_exchange_probe",
    ]

    assert _table_exists(probe_backend, "exchange_probe")
    assert _table_exists(probe_backend, "exchange_probe_old")
    assert not _table_exists(probe_backend, "exchange_probe_next")
    assert _column_exists(probe_backend, "exchange_probe", "value")
    assert not _column_exists(probe_backend, "exchange_probe", "legacy_value")


def test_exchange_migration_swaps_back_on_down(probe_backend, tmp_path):
    store = JSONFileMigrationRecordStore(tmp_path / "exchange_down.json")
    run_migration_group(
        probe_backend,
        [create_exchange_probe, swap_exchange_probe],
        record_store=store,
    )

    run_migration_group(
        probe_backend,
        [swap_exchange_probe],
        direction=MigrationDirection.DOWN,
        record_store=store,
    )

    assert _table_exists(probe_backend, "exchange_probe")
    assert not _table_exists(probe_backend, "exchange_probe_old")
    assert not _table_exists(probe_backend, "exchange_probe_next")
    assert _column_exists(probe_backend, "exchange_probe", "legacy_value")
    assert not _column_exists(probe_backend, "exchange_probe", "value")
