# tests/rhosocial/activerecord_test/feature/backend/sqlite/expression/test_namespace_and_insert.py
"""Cover the SQLite expression namespace re-exports and its OR IGNORE insert."""

import pytest

from rhosocial.activerecord.backend.expression import Column, QueryStatement
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import SelectSource
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression import functions, statements
from rhosocial.activerecord.backend.impl.sqlite.expression.statements import (
    SQLiteInsertStatement,
)

DIALECT = SQLiteDialect(version=(3, 53, 0))


def test_lazy_namespace_reexports_resolve_and_refuse():
    """A namespace resolves public names lazily and refuses unknown ones."""
    assert functions.SQLiteJsonExtractFunction is not None
    assert statements.SQLiteInsertStatement is not None
    with pytest.raises(AttributeError):
        functions._no_such_name_
    with pytest.raises(AttributeError):
        statements._no_such_name_


def test_sqlite_insert_or_ignore_renders_its_own_spelling():
    """SQLiteInsertStatement's typed flags reach the SQLite renderer."""
    query = QueryStatement(DIALECT, select=[Column(DIALECT, "id")], from_="staging")
    stmt = SQLiteInsertStatement(
        DIALECT,
        into=Table(DIALECT, "events"),
        source=SelectSource(DIALECT, query),
        or_ignore=True,
    )
    sql, params = stmt.to_sql()
    assert sql.startswith("INSERT OR IGNORE INTO")
    assert 'SELECT "id" FROM "staging"' in sql
    assert params == ()
