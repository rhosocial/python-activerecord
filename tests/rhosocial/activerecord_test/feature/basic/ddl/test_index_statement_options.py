# tests/rhosocial/activerecord_test/feature/basic/ddl/test_index_statement_options.py
"""ActiveRecord-level tests for index statement-level options (§5.16).

``UseIndex`` (field-level) and ``IndexDefinition`` (table-level) carry
``if_not_exists`` / ``tablespace`` / ``concurrent`` (create) and ``if_exists``
(drop); the deriver passes them through to the standalone CREATE/DROP INDEX
statements, and the inline CREATE TABLE path rejects the create-side options
because it cannot carry them.
"""

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.base import UseIndex
from rhosocial.activerecord.ddl import TableDDLDeriver
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    IndexDefinition,
)
from rhosocial.activerecord.backend.impl.dummy import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.model import ActiveRecord


class FieldIndexed(ActiveRecord):
    __table_name__ = "field_indexed"

    id: int
    email: Annotated[
        str,
        UseIndex(
            "idx_email",
            unique=True,
            if_not_exists=True,
            tablespace="ts_fast",
            concurrent=True,
        ),
    ]
    code: Annotated[str, UseIndex("idx_code", if_exists=True)]


class TableIndexed(ActiveRecord):
    __table_name__ = "table_indexed"

    id: int
    __table_indexes__ = [
        IndexDefinition(
            None,
            name="idx_table",
            columns=["id"],
            if_not_exists=True,
            tablespace="ts_x",
            concurrent=True,
            if_exists=True,
        ),
    ]


class InlineDialect(DummyDialect):
    """A dialect that can inline indexes into CREATE TABLE."""

    def supports_inline_index(self) -> bool:
        return True


class PermissiveDialect(DummyDialect):
    """A dialect that supports every statement-level index option."""

    def supports_index_if_not_exists(self) -> bool:
        return True

    def supports_index_if_exists(self) -> bool:
        return True

    def supports_index_tablespace(self) -> bool:
        return True

    def supports_concurrent_index(self) -> bool:
        return True


SQLITE = SQLiteDialect((3, 53, 0))


def _create_by_name(model, dialect):
    return {expr.index_name: expr for expr in TableDDLDeriver(model, dialect).create_indexes()}


def _drop_by_name(model, dialect, **kwargs):
    return {
        expr.index_name: expr
        for expr in TableDDLDeriver(model, dialect).drop_indexes(**kwargs)
    }


# ---------------------------------------------------------------------------
# Declaration -> statement passthrough
# ---------------------------------------------------------------------------


def test_field_level_create_options_pass_through():
    by_name = _create_by_name(FieldIndexed, SQLITE)
    email = by_name["idx_email"]
    assert email.if_not_exists is True
    assert email.tablespace == "ts_fast"
    assert email.concurrent is True
    # An index without the options stays at the dialect-safe default.
    assert by_name["idx_code"].if_not_exists is False
    assert by_name["idx_code"].tablespace is None


def test_table_level_create_options_pass_through():
    expr = _create_by_name(TableIndexed, SQLITE)["idx_table"]
    assert expr.if_not_exists is True
    assert expr.tablespace == "ts_x"
    assert expr.concurrent is True


def test_drop_per_index_if_exists_wins_over_entry_param():
    by_name = _drop_by_name(FieldIndexed, SQLITE)
    # idx_code declares if_exists=True explicitly; idx_email does not, so it
    # falls back to the entry parameter (False here).
    assert by_name["idx_code"].if_exists is True
    assert by_name["idx_email"].if_exists is False


def test_drop_entry_param_is_the_fallback():
    by_name = _drop_by_name(FieldIndexed, SQLITE, if_exists=True)
    assert by_name["idx_email"].if_exists is True


def test_drop_concurrent_passes_through():
    by_name = _drop_by_name(FieldIndexed, SQLITE)
    assert by_name["idx_email"].concurrent is True
    assert by_name["idx_code"].concurrent is False


# ---------------------------------------------------------------------------
# Rendering on a permissive dialect
# ---------------------------------------------------------------------------


def test_create_index_renders_statement_options():
    expr = _create_by_name(FieldIndexed, PermissiveDialect())["idx_email"]
    sql, _ = expr.to_sql()
    assert sql.startswith("CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS")
    assert "TABLESPACE \"ts_fast\"" in sql


def test_drop_index_renders_statement_options():
    expr = _drop_by_name(FieldIndexed, PermissiveDialect(), if_exists=True)["idx_email"]
    sql, _ = expr.to_sql()
    assert "IF EXISTS" in sql
    assert "CONCURRENTLY" in sql


# ---------------------------------------------------------------------------
# Inline path gating
# ---------------------------------------------------------------------------


def test_inline_path_rejects_statement_options():
    deriver = TableDDLDeriver(FieldIndexed, InlineDialect())
    with pytest.raises(ValueError, match="inline index"):
        deriver.create_table()


def test_inline_path_accepts_plain_indexes():
    class PlainInline(ActiveRecord):
        __table_name__ = "plain_inline"

        id: int
        email: Annotated[str, UseIndex("idx_plain", unique=True)]

    expression = TableDDLDeriver(PlainInline, InlineDialect()).create_table()
    assert [index.name for index in expression.indexes] == ["idx_plain"]
