# tests/rhosocial/activerecord_test/feature/basic/ddl/test_comment_clauses.py
"""Inline comment clauses vs. the standalone COMMENT ON statement.

Covers the deliberate separation the DDL layer draws:

* ``ColumnCommentClause`` / ``TableCommentClause`` — the CREATE TABLE inline
  comment *clauses* (part of the statement grammar; MySQL/MariaDB/ClickHouse
  family, BigQuery, Snowflake);
* ``CommentOnExpression`` — the standalone ``COMMENT ON`` *statement* that
  annotates existing objects (PostgreSQL/Oracle/Firebird/Snowflake), rendered
  by the generic ``CommentOnMixin``.

The two are **not** interchangeable, and the tests pin the generic rendering,
capability gating, and the fixed spacing between the column list and the
table-comment clause.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.statements import (
    ColumnCommentClause,
    ColumnDefinition,
    CommentObjectType,
    CommentOnExpression,
    CreateTableExpression,
    CreateTableOptions,
    TableCommentClause,
)
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.impl.dummy import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


@pytest.fixture
def dummy():
    return DummyDialect()


@pytest.fixture
def sqlite():
    return SQLiteDialect((3, 53, 0))


# ---------------------------------------------------------------------------
# Inline column-comment clause
# ---------------------------------------------------------------------------


def test_column_comment_clause_renders_with_leading_space(dummy):
    clause = ColumnCommentClause(dummy, "a note")
    assert dummy.format_column_comment_clause(clause) == (" COMMENT 'a note'", ())


def test_column_comment_clause_escapes_quotes(dummy):
    clause = ColumnCommentClause(dummy, "it's")
    assert dummy.format_column_comment_clause(clause) == (" COMMENT 'it''s'", ())


def test_column_definition_rejects_bare_string(dummy):
    with pytest.raises(TypeError, match="ColumnCommentClause"):
        ColumnDefinition(dummy, "c", IntegerType(dummy), comment="bare string")


def test_column_definition_renders_clause(dummy):
    col = ColumnDefinition(
        dummy, "c", IntegerType(dummy), comment=ColumnCommentClause(dummy, "a note")
    )
    assert col.to_sql()[0].endswith(" COMMENT 'a note'")


def test_column_comment_clause_gated(sqlite):
    clause = ColumnCommentClause(sqlite, "x")
    with pytest.raises(UnsupportedFeatureError, match="COLUMN COMMENT"):
        sqlite.format_column_comment_clause(clause)


# ---------------------------------------------------------------------------
# Inline table-comment clause
# ---------------------------------------------------------------------------


def test_table_comment_clause_renders_with_leading_space(dummy):
    clause = TableCommentClause(dummy, "hello world")
    assert dummy.format_table_comment_clause(clause) == (" COMMENT 'hello world'", ())


def test_create_table_options_rejects_bare_string(dummy):
    with pytest.raises(TypeError, match="TableCommentClause"):
        CreateTableOptions(dummy, comment="bare string")


def test_generic_create_table_table_comment_spacing(dummy):
    """The table-comment clause must be separated from the column list."""
    col = ColumnDefinition(dummy, "id", IntegerType(dummy))
    expr = CreateTableExpression(
        dummy,
        "t",
        [col],
        table_options=CreateTableOptions(
            dummy, comment=TableCommentClause(dummy, "hello world")
        ),
    )
    sql, params = expr.to_sql()
    assert sql == 'CREATE TABLE "t" ("id" INTEGER) COMMENT \'hello world\''
    assert ")COMMENT" not in sql
    assert params == ()


def test_table_comment_clause_gated(sqlite):
    clause = TableCommentClause(sqlite, "x")
    with pytest.raises(UnsupportedFeatureError, match="TABLE COMMENT"):
        sqlite.format_table_comment_clause(clause)


# ---------------------------------------------------------------------------
# Standalone COMMENT ON statement
# ---------------------------------------------------------------------------


def test_comment_on_table(dummy):
    sql, params = CommentOnExpression(
        dummy, CommentObjectType.TABLE, "t", "meta"
    ).to_sql()
    assert sql == 'COMMENT ON TABLE "t" IS \'meta\''
    assert params == ()


def test_comment_on_column_dotted_target(dummy):
    sql, _ = CommentOnExpression(
        dummy, CommentObjectType.COLUMN, "t.c", "col"
    ).to_sql()
    assert sql == 'COMMENT ON COLUMN "t"."c" IS \'col\''


def test_comment_on_schema_qualified(dummy):
    sql, _ = CommentOnExpression(
        dummy, CommentObjectType.TABLE, "t", "x", schema="s"
    ).to_sql()
    assert sql == 'COMMENT ON TABLE "s"."t" IS \'x\''


def test_comment_on_null_clears(dummy):
    sql, params = CommentOnExpression(dummy, CommentObjectType.TABLE, "t", None).to_sql()
    assert sql == 'COMMENT ON TABLE "t" IS NULL'
    assert params == ()


def test_comment_on_escapes_apostrophe(dummy):
    sql, _ = CommentOnExpression(dummy, CommentObjectType.TABLE, "t", "it's").to_sql()
    assert sql == "COMMENT ON TABLE \"t\" IS 'it''s'"


def test_comment_on_accepts_string_object_type(dummy):
    sql, _ = CommentOnExpression(dummy, "TABLE", "t", "x").to_sql()
    assert sql == 'COMMENT ON TABLE "t" IS \'x\''


def test_comment_on_empty_object_name_rejected(dummy):
    with pytest.raises(ValueError, match="object_name"):
        CommentOnExpression(dummy, CommentObjectType.TABLE, "   ", "x")


def test_comment_on_gated_by_default(sqlite):
    """A dialect without COMMENT ON raises a clean UnsupportedFeatureError."""
    assert sqlite.supports_comment_on() is False
    with pytest.raises(UnsupportedFeatureError, match="COMMENT ON"):
        CommentOnExpression(sqlite, CommentObjectType.TABLE, "t", "x").to_sql()
