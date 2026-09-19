# tests/rhosocial/activerecord_test/feature/basic/ddl/test_inline_index_capability.py
"""Tests for the inline-index capability (supports_inline_index) and the
ActiveRecord-layer auto-routing of index placement.

Design contract (see .claude/plan/2026-09-19/create-table-inline-index-capability.md):

- SQL-standard CREATE TABLE carries no index definitions; inline indexes are a
  MySQL/MariaDB/ClickHouse dialect convenience gated by
  ``supports_inline_index()``.
- The generic ``format_create_table_statement`` raises UnsupportedFeatureError
  when an expression carries indexes but the dialect has no inline support
  (never silently dropped).
- ``create_table()`` is a dialect-sensitive snapshot; ``create_indexes()``
  covers only what cannot be inlined; the union is always the full declared
  index set, without overlap.
"""

from typing import Optional

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.base import UseIndex
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.expression.statements.ddl_index import (
    CreateIndexExpression,
    DropIndexExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnDefinition,
    CreateTableExpression,
    IndexDefinition,
)
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.impl.dummy import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.model import ActiveRecord


class Indexed(ActiveRecord):
    __table_name__ = "indexed"

    id: int
    email: Annotated[str, UseIndex("idx_indexed_email", unique=True)]
    name: Optional[str]


@pytest.fixture
def backend():
    instance = SQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
    Indexed.__backend__ = instance
    return instance


# ---------------------------------------------------------------------------
# Capability defaults (protocol-level)
# ---------------------------------------------------------------------------


def test_dummy_supports_inline_index_default_false():
    assert DummyDialect().supports_inline_index() is False


def test_sqlite_supports_inline_index_default_false():
    assert SQLiteDialect((3, 53, 0)).supports_inline_index() is False


# ---------------------------------------------------------------------------
# Generic renderer guard: never silently drop indexes
# ---------------------------------------------------------------------------


def _indexed_create_table(dialect, indexes):
    return CreateTableExpression(
        dialect,
        "t",
        columns=[ColumnDefinition(dialect, "id", IntegerType(dialect))],
        indexes=indexes,
    )


def test_generic_create_table_with_indexes_raises():
    dialect = DummyDialect()
    expr = _indexed_create_table(
        dialect, [IndexDefinition(dialect, name="idx_t_id", columns=["id"])]
    )
    with pytest.raises(UnsupportedFeatureError, match="inline index"):
        expr.to_sql()


def test_generic_create_table_without_indexes_ok():
    dialect = DummyDialect()
    sql, params = _indexed_create_table(dialect, []).to_sql()
    assert '"t"' in sql
    assert params == ()


# ---------------------------------------------------------------------------
# ActiveRecord layer: snapshot / remainder split
# ---------------------------------------------------------------------------


def test_deriver_sqlite_snapshot_carries_no_indexes(backend):
    # SQLite has no inline index support: CREATE TABLE carries no indexes.
    assert Indexed.create_table().indexes == []


def test_deriver_sqlite_create_indexes_covers_all(backend):
    statements = Indexed.create_indexes()
    assert len(statements) == 1
    assert isinstance(statements[0], CreateIndexExpression)
    assert statements[0].index_name == "idx_indexed_email"
    assert statements[0].table_name == "indexed"
    assert statements[0].unique is True


def test_deriver_create_schema_completeness(backend):
    plan = Indexed.create_schema()
    assert isinstance(plan[0], CreateTableExpression)
    standalone = [expr for expr in plan if isinstance(expr, CreateIndexExpression)]
    declared = Indexed.table_indexes()
    # Union of inline + standalone indexes equals the declared set, no overlap.
    assert plan[0].indexes == []
    assert [expr.index_name for expr in standalone] == [i.name for i in declared]


def test_deriver_drop_schema_orders_indexes_first(backend):
    plan = Indexed.drop_schema()
    assert isinstance(plan[0], DropIndexExpression)
    assert plan[0].index_name == "idx_indexed_email"
    assert plan[-1].table.name == "indexed"


def test_deriver_inline_indexes_override_true_raises_on_sqlite(backend):
    # Explicit intent conflicts with capability -> visible error, not silence.
    expression = Indexed.create_table(inline_indexes=True)
    assert [index.name for index in expression.indexes] == ["idx_indexed_email"]
    with pytest.raises(UnsupportedFeatureError, match="inline index"):
        expression.to_sql()


def test_deriver_inline_indexes_override_false_forces_standalone(backend):
    expression = Indexed.create_table(inline_indexes=False)
    assert expression.indexes == []


# ---------------------------------------------------------------------------
# CREATE INDEX / DROP INDEX capability gates
# ---------------------------------------------------------------------------


def test_create_index_gate_index_type():
    dialect = SQLiteDialect((3, 53, 0))
    expr = CreateIndexExpression(
        dialect, index_name="idx", table_name="t", columns=["c"], index_type="HASH"
    )
    with pytest.raises(UnsupportedFeatureError, match="index type"):
        expr.to_sql()


def test_create_index_gate_partial():
    class NoPartialDialect(DummyDialect):
        def supports_partial_index(self) -> bool:
            return False

    dialect = NoPartialDialect()
    predicate = Column(dialect, "c") == 1
    expr = CreateIndexExpression(
        dialect, index_name="idx", table_name="t", columns=["c"], where=predicate
    )
    with pytest.raises(UnsupportedFeatureError, match="partial"):
        expr.to_sql()


def test_drop_index_on_table_capability():
    # SQLite/Postgres-style: no ON <table> suffix.
    dialect = SQLiteDialect((3, 53, 0))
    sql, _ = DropIndexExpression(dialect, index_name="idx", table_name="t").to_sql()
    assert sql == 'DROP INDEX "idx"'

    # MySQL-style (default): ON <table> rendered.
    dummy = DummyDialect()
    sql, _ = DropIndexExpression(dummy, index_name="idx", table_name="t").to_sql()
    assert sql == 'DROP INDEX "idx" ON "t"'

