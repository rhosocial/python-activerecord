# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_sqlite_statement_acceptance.py
"""The SQL the framework renders must be SQL SQLite accepts.

Every other test in this package asserts the *shape* of a statement: which
options it carries, which names it quotes, how many parameters it holds.
That is a real check, and it is not enough. A statement can have exactly
the shape it should and still be one the server refuses to run -- the
shape says nothing about whether the server agrees.

Two defects were found this way: an R-Tree statement whose option count
made the column total even, and a Geopoly statement carrying an option
Geopoly does not have. Both passed every test that existed, because every
test that existed compared text.

So the rule this file pins is simple: the statement the framework renders
is handed to a real SQLite and executed. A rejection is the failure.

Each case carries the setup the statement needs, and a fragment is placed
where it belongs -- a predicate belongs in a WHERE clause, a function call
belongs in a SELECT list -- because a fragment judged out of context says
nothing about the framework.
"""

import sqlite3

from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.attach import (
    SQLiteAttachExpression,
    SQLiteDetachExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.fts5 import (
    SQLiteFTS5CreateVirtualTable,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.json import (
    SQLiteJsonExtractFunction,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.predicates import (
    SQLiteMatchPredicate,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.reindex import (
    SQLiteReindexStatement,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.rtree import (
    SQLiteRTreeCreateVirtualTable,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.vacuum import (
    SQLiteAnalyzeStatement,
    SQLiteVacuumStatement,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.virtual_table import (
    CreateVirtualTableStatement,
    DropVirtualTableStatement,
)

DIALECT = SQLiteDialect(version=(3, 40, 0))


def accepts(sql, setup=(), params=()):
    """Execute *sql* on a fresh SQLite; a rejection raises."""
    connection = sqlite3.connect(":memory:")
    try:
        for statement in setup:
            connection.execute(statement)
        connection.execute(sql, tuple(params))
    finally:
        connection.close()


def rendered(expr):
    """The statement the framework renders for *expr*."""
    return expr.to_sql()


class TestRTreeStatements:
    """R-Tree counts content= and content_rowid= as columns of its own."""

    def test_plain(self):
        sql, _ = rendered(
            SQLiteRTreeCreateVirtualTable(DIALECT, table=Table(DIALECT, "t"), dimensions=2)
        )
        accepts(sql)

    def test_with_a_content_table(self):
        sql, _ = rendered(
            SQLiteRTreeCreateVirtualTable(
                DIALECT,
                table=Table(DIALECT, "t"),
                dimensions=2,
                content_table=Table(DIALECT, "src"),
            )
        )
        accepts(sql, setup=["CREATE TABLE src(id INTEGER PRIMARY KEY, minX REAL, maxX REAL)"])

    def test_with_a_content_table_and_a_named_rowid(self):
        sql, _ = rendered(
            SQLiteRTreeCreateVirtualTable(
                DIALECT,
                table=Table(DIALECT, "t"),
                dimensions=2,
                content_table=Table(DIALECT, "src"),
                content_rowid="id",
            )
        )
        accepts(sql, setup=["CREATE TABLE src(id INTEGER PRIMARY KEY, minX REAL, maxX REAL)"])

    def test_three_dimensions(self):
        sql, _ = rendered(
            SQLiteRTreeCreateVirtualTable(DIALECT, table=Table(DIALECT, "t"), dimensions=3)
        )
        accepts(sql)


class TestFTS5Statements:
    """FTS5's content options are not columns, so either may stand alone."""

    def test_plain(self):
        sql, _ = rendered(
            SQLiteFTS5CreateVirtualTable(DIALECT, table=Table(DIALECT, "ft"), columns=["a", "b"])
        )
        accepts(sql)

    def test_with_a_content_table(self):
        sql, _ = rendered(
            SQLiteFTS5CreateVirtualTable(
                DIALECT, table=Table(DIALECT, "ft"), columns=["a"], content="src"
            )
        )
        accepts(sql, setup=["CREATE TABLE src(id INTEGER PRIMARY KEY, a TEXT)"])

    def test_with_a_content_table_and_a_named_rowid(self):
        sql, _ = rendered(
            SQLiteFTS5CreateVirtualTable(
                DIALECT,
                table=Table(DIALECT, "ft"),
                columns=["a"],
                content="src",
                content_rowid="id",
            )
        )
        accepts(sql, setup=["CREATE TABLE src(id INTEGER PRIMARY KEY, a TEXT)"])

    def test_with_a_rowid_name_alone(self):
        sql, _ = rendered(
            SQLiteFTS5CreateVirtualTable(
                DIALECT, table=Table(DIALECT, "ft"), columns=["a"], content_rowid="id"
            )
        )
        accepts(sql)

    def test_with_a_tokenizer(self):
        sql, _ = rendered(
            SQLiteFTS5CreateVirtualTable(
                DIALECT, table=Table(DIALECT, "ft"), columns=["a"], tokenize="porter"
            )
        )
        accepts(sql)

    def test_with_prefix_indexes(self):
        sql, _ = rendered(
            SQLiteFTS5CreateVirtualTable(
                DIALECT, table=Table(DIALECT, "ft"), columns=["a"], prefix=[2, 3]
            )
        )
        accepts(sql)


class TestMaintenanceStatements:
    """VACUUM, ANALYZE, ATTACH, DETACH and REINDEX."""

    def test_vacuum(self):
        sql, _ = rendered(SQLiteVacuumStatement(DIALECT))
        accepts(sql)

    def test_vacuum_into(self, tmp_path):
        sql, _ = rendered(SQLiteVacuumStatement(DIALECT, into=str(tmp_path / "out.db")))
        connection = sqlite3.connect(":memory:")
        try:
            connection.execute("CREATE TABLE t(a)")
            connection.execute("INSERT INTO t VALUES (1)")
            connection.commit()
            connection.execute(sql)
        finally:
            connection.close()

    def test_analyze(self):
        sql, _ = rendered(SQLiteAnalyzeStatement(DIALECT))
        accepts(sql)

    def test_attach(self):
        # ':memory:' so the attach leaves no file behind.
        sql, _ = rendered(SQLiteAttachExpression(DIALECT, database=":memory:", schema="o"))
        accepts(sql)

    def test_detach(self):
        sql, _ = rendered(SQLiteDetachExpression(DIALECT, schema="o"))
        accepts(sql, setup=["ATTACH DATABASE ':memory:' AS o"])

    def test_reindex(self):
        sql, _ = rendered(SQLiteReindexStatement(DIALECT))
        accepts(sql)


class TestVirtualTableStatements:
    """CREATE and DROP of a virtual table."""

    def test_create(self):
        sql, _ = rendered(
            CreateVirtualTableStatement(
                DIALECT,
                module="rtree",
                table=Table(DIALECT, "v"),
                columns=["id", "minX", "maxX"],
            )
        )
        accepts(sql)

    def test_drop(self):
        sql, _ = rendered(DropVirtualTableStatement(DIALECT, table=Table(DIALECT, "v")))
        accepts(sql, setup=["CREATE VIRTUAL TABLE v USING rtree(id, minX, maxX)"])


class TestJsonAndMatchFragments:
    """A function call and a predicate, each where it belongs."""

    def test_json_extract_as_a_select_item(self):
        sql, params = rendered(
            SQLiteJsonExtractFunction(
                DIALECT, expression=Column(DIALECT, "j"), path=Column(DIALECT, "p")
            )
        )
        accepts(
            f"SELECT {sql} FROM t",
            setup=["CREATE TABLE t(j TEXT, p TEXT)"],
            params=params,
        )

    def test_match_predicate_in_a_where_clause(self):
        sql, params = rendered(SQLiteMatchPredicate(DIALECT, table="ft", query="hello"))
        accepts(
            f"SELECT * FROM ft WHERE {sql}",
            setup=["CREATE VIRTUAL TABLE ft USING fts5(x)"],
            params=params,
        )
