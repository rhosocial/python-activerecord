# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/statements/test_stmt_dml_surface.py
"""SQLite's INSERT surface: the three source shapes and its own spellings.

``INSERT OR REPLACE`` / ``INSERT OR IGNORE`` are SQLite spellings the shared
renderer does not know; the SQLite override spells them. ``strict_validation``
is the one gate the render path consults before trusting the node.
"""

import pytest

from rhosocial.activerecord.backend.expression import Column, Literal, QueryStatement
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    DefaultValuesSource,
    InsertDataSource,
    InsertStatement,
    OnConflictClause,
    SelectSource,
    ValuesSource,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

DIALECT = SQLiteDialect(version=(3, 53, 0))


def _select_source():
    return QueryStatement(DIALECT, select=[Column(DIALECT, "id")], from_="staging")


def test_default_values_source():
    sql, params = InsertStatement(
        DIALECT, into=Table(DIALECT, "events"), source=DefaultValuesSource(DIALECT)
    ).to_sql()
    assert sql.startswith('INSERT INTO "events"')
    assert "DEFAULT VALUES" in sql
    assert params == ()


def test_select_source_with_or_replace():
    sql, params = InsertStatement(
        DIALECT,
        into=Table(DIALECT, "events"),
        source=SelectSource(DIALECT, _select_source()),
        or_replace=True,
    ).to_sql()
    assert sql.startswith("INSERT OR REPLACE INTO")
    assert 'SELECT "id" FROM "staging"' in sql
    assert params == ()


def test_values_source_with_columns_and_on_conflict():
    sql, params = InsertStatement(
        DIALECT,
        into=Table(DIALECT, "counters"),
        columns=["name", "hits"],
        source=ValuesSource(DIALECT, values_list=[[Literal(DIALECT, "page"), Literal(DIALECT, 1)]]),
        on_conflict=OnConflictClause(
            DIALECT, ["name"], update_assignments={"hits": Literal(DIALECT, 2)}
        ),
    ).to_sql()
    assert sql.startswith('INSERT INTO "counters" ("name", "hits") VALUES (?, ?)')
    assert 'ON CONFLICT ("name") DO UPDATE SET "hits" = ?' in sql
    assert params == ("page", 1, 2)


def test_strict_validation_gate_can_be_turned_off():
    dialect = SQLiteDialect(version=(3, 53, 0))
    dialect.strict_validation = False
    sql, params = InsertStatement(
        dialect,
        into=Table(dialect, "events"),
        source=ValuesSource(dialect, values_list=[[Literal(dialect, 1)]]),
    ).to_sql()
    assert sql.startswith('INSERT INTO "events"')
    assert params == (1,)


def test_returning_alias_is_spelled_after_the_clause():
    from rhosocial.activerecord.backend.expression.statements import ReturningClause

    clause = ReturningClause(DIALECT, expressions=[Column(DIALECT, "id")], alias="new_rows")
    sql, params = clause.to_sql()
    assert sql == 'RETURNING "id" AS "new_rows"'
    assert params == ()


def test_a_source_outside_the_three_shapes_is_refused():
    """``InsertDataSource`` has exactly three subclasses; anything else is a bug.

    Rendering an unknown source used to fall through with an empty source and
    emit ``INSERT INTO t`` -- a statement that inserts nothing. The render path
    now refuses it instead.
    """

    class _AlienSource(InsertDataSource):
        @property
        def format_method(self):
            return "format_insert_default_values_source"

    with pytest.raises(TypeError, match="Unsupported INSERT source"):
        InsertStatement(
            DIALECT, into=Table(DIALECT, "events"), source=_AlienSource(DIALECT)
        ).to_sql()
