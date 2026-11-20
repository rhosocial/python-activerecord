# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/expressions/test_expr_sqlite_specific_nodes.py
"""Constructor validation for SQLite-specific expression nodes."""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

DIALECT = SQLiteDialect(version=(3, 53, 0))


def test_fts5_nodes_reject_non_table():
    from rhosocial.activerecord.backend.impl.sqlite.expression.fts5 import (
        SQLiteFTS5CreateVirtualTable,
        SQLiteFTS5HighlightExpression,
        SQLiteFTS5RankExpression,
        SQLiteFTS5SnippetExpression,
    )

    with pytest.raises(TypeError):
        SQLiteFTS5CreateVirtualTable(DIALECT, table="docs", columns=["body"])
    with pytest.raises(TypeError):
        SQLiteFTS5RankExpression(DIALECT, table="docs")
    with pytest.raises(TypeError):
        SQLiteFTS5HighlightExpression(DIALECT, table="docs", column="body")
    with pytest.raises(TypeError):
        SQLiteFTS5SnippetExpression(DIALECT, table="docs", column="body")


def test_geopoly_nodes_reject_non_table():
    from rhosocial.activerecord.backend.impl.sqlite.expression.geopoly import (
        SQLiteGeopolyAreaExpression,
        SQLiteGeopolyContainsExpression,
        SQLiteGeopolyCreateVirtualTable,
    )

    with pytest.raises(TypeError):
        SQLiteGeopolyCreateVirtualTable(DIALECT, table="places")
    with pytest.raises(TypeError):
        SQLiteGeopolyContainsExpression(DIALECT, table="places", longitude=1, latitude=2)
    with pytest.raises(TypeError):
        SQLiteGeopolyAreaExpression(DIALECT, table="places")


def test_rtree_nodes_and_reindex_validation():
    from rhosocial.activerecord.backend.expression.objects import Index, Table
    from rhosocial.activerecord.backend.impl.sqlite.expression.reindex import (
        SQLiteReindexStatement,
    )
    from rhosocial.activerecord.backend.impl.sqlite.expression.rtree import (
        SQLiteRTreeCreateVirtualTable,
        SQLiteRTreeRangeQuery,
    )

    with pytest.raises(TypeError):
        SQLiteRTreeCreateVirtualTable(DIALECT, table="places")
    with pytest.raises(TypeError):
        SQLiteRTreeCreateVirtualTable(
            DIALECT, table=Table(DIALECT, "places"), content_table="places"
        )
    with pytest.raises(TypeError):
        SQLiteRTreeRangeQuery(DIALECT, table="places", ranges=[])

    with pytest.raises(ValueError):
        SQLiteReindexStatement(DIALECT, index=Index(DIALECT, "ix"), table=Table(DIALECT, "t"))
    with pytest.raises(ValueError):
        SQLiteReindexStatement(DIALECT, expressions=True, index=Index(DIALECT, "ix"))
    with pytest.raises(TypeError):
        SQLiteReindexStatement(DIALECT, index="ix")
    with pytest.raises(TypeError):
        SQLiteReindexStatement(DIALECT, table="t")


def test_virtual_table_nodes_reject_non_table():
    from rhosocial.activerecord.backend.impl.sqlite.expression.virtual_table import (
        CreateVirtualTableStatement,
        DropVirtualTableStatement,
    )

    with pytest.raises(TypeError):
        CreateVirtualTableStatement(DIALECT, module="fts5", table="docs", columns=["body"])
    with pytest.raises(TypeError):
        DropVirtualTableStatement(DIALECT, table="docs")


def test_fts5_and_virtual_table_format_methods():
    from rhosocial.activerecord.backend.expression.objects import Table
    from rhosocial.activerecord.backend.impl.sqlite.expression.fts5 import (
        SQLiteFTS5MatchPredicate,
    )
    from rhosocial.activerecord.backend.impl.sqlite.expression.virtual_table import (
        CreateVirtualTableStatement,
        DropVirtualTableStatement,
    )

    assert SQLiteFTS5MatchPredicate(DIALECT, "docs", "x").format_method == (
        "format_fts5_match_expression"
    )
    create = CreateVirtualTableStatement(
        DIALECT, module="fts5", table=Table(DIALECT, "docs"), columns=["body"]
    )
    drop = DropVirtualTableStatement(DIALECT, table=Table(DIALECT, "docs"))
    assert create.format_method == "format_create_virtual_table_statement"
    assert drop.format_method == "format_drop_virtual_table_statement"
