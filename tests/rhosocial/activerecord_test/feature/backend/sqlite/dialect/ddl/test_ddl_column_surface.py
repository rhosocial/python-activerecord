# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/ddl/test_ddl_column_surface.py
"""SQLite column definitions: boolean defaults, AUTOINCREMENT placement, comments.

Three SQLite-only rules live on the column definition rather than in the shared
renderer: booleans become ``1``/``0``, ``AUTOINCREMENT`` is legal only on an
``INTEGER PRIMARY KEY``, and an inline column comment has no spelling at all.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.statements import (
    ColumnCommentClause,
    ColumnConstraint,
    ColumnDefinition,
    ColumnPrimaryKeyConstraint,
    DefaultValueClause,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
    SQLiteIntegerType,
    SQLiteTextType,
)

DIALECT = SQLiteDialect(version=(3, 53, 0))


def _auto_increment_constraint():
    return ColumnConstraint(
        DIALECT, branch=ColumnPrimaryKeyConstraint(DIALECT, is_auto_increment=True)
    )


def test_boolean_default_is_inlined_as_one_or_zero():
    assert DefaultValueClause(DIALECT, True).to_sql() == ("1", ())
    assert DefaultValueClause(DIALECT, False).to_sql() == ("0", ())


def test_auto_increment_on_integer_primary_key_renders():
    sql, params = ColumnDefinition(
        DIALECT,
        "id",
        SQLiteIntegerType(DIALECT),
        constraints=[_auto_increment_constraint()],
    ).to_sql()
    assert sql == '"id" INTEGER PRIMARY KEY AUTOINCREMENT'
    assert params == ()


def test_auto_increment_on_non_integer_is_refused():
    with pytest.raises(UnsupportedFeatureError, match="AUTOINCREMENT"):
        ColumnDefinition(
            DIALECT,
            "name",
            SQLiteTextType(DIALECT),
            constraints=[_auto_increment_constraint()],
        ).to_sql()


def test_primary_key_without_auto_increment_has_no_tail():
    plain = ColumnConstraint(DIALECT, branch=ColumnPrimaryKeyConstraint(DIALECT))
    sql, _ = ColumnDefinition(
        DIALECT, "id", SQLiteIntegerType(DIALECT), constraints=[plain]
    ).to_sql()
    assert sql == '"id" INTEGER PRIMARY KEY'


def test_inline_column_comment_is_refused():
    with pytest.raises(UnsupportedFeatureError, match="COLUMN COMMENT"):
        ColumnDefinition(
            DIALECT,
            "name",
            SQLiteTextType(DIALECT),
            comment=ColumnCommentClause(DIALECT, "display name"),
        ).to_sql()
