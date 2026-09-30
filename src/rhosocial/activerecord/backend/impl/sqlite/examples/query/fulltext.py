# src/rhosocial/activerecord/backend/impl/sqlite/examples/query/fulltext.py
"""
Full-Text Search (FTS5): create virtual table, insert documents, and search
using MATCH, prefix, phrase, and NEAR queries.

This example demonstrates using the SQLite dialect's FTS5 formatting
methods (format_fts5_create_virtual_table) and the Expression API
(InsertExpression, QueryExpression with SQLiteMatchPredicate) to avoid
writing raw SQL strings directly.

SQLiteMatchPredicate is a SQLite-specific expression class for full-text search
MATCH predicates. It delegates to the dialect's format_match_predicate
method, which in turn calls the FTS5 extension's formatting logic.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.expression import (
    InsertExpression,
    Literal,
    QueryExpression,
    TableExpression,
    ValuesSource,
    WildcardExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.expression import (
    SQLiteFTS5CreateVirtualTable,
    SQLiteMatchPredicate,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect


# Version-gated features (RETURNING, JSON1, math functions) read the
# dialect version, which is only known after the server is inspected.
backend.introspect_and_adapt()
# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
# The MATCH queries below all read a virtual FTS5 table, so create it first --
# a MATCH against a table that does not exist is a QueryError, not an empty
# result. SQLiteFTS5CreateVirtualTable renders CREATE VIRTUAL TABLE ... USING
# fts5, which is how FTS is declared; there is no plain CREATE TABLE equivalent.
create_docs = SQLiteFTS5CreateVirtualTable(
    dialect, table_name="docs", columns=["title", "body"]
)
sql, _ = create_docs.to_sql()
print(f"SQL: {sql}")
backend.execute(sql, ())

insert_docs = InsertExpression(
    dialect=dialect,
    into="docs",
    columns=["title", "body"],
    source=ValuesSource(
        dialect,
        [
            # 'Python' and 'web' in the same column, so the NEAR query can match:
            # NEAR does not span columns by default.
            [Literal(dialect, "Python basics"), Literal(dialect, "python and web frameworks")],
            [Literal(dialect, "Advanced Python"), Literal(dialect, "async patterns in python")],
            # a word starting with 'prog', for the prefix query
            [Literal(dialect, "Programming guides"), Literal(dialect, "progressive disclosure")],
        ],
    ),
)
sql, params = insert_docs.to_sql()
backend.execute(sql, params)

# SQLiteMatchPredicate delegates to the SQLite dialect's FTS5 formatting.
match_pred = SQLiteMatchPredicate(dialect, table="docs", query="Python")

prefix_pred = SQLiteMatchPredicate(dialect, table="docs", query="prog*")

phrase_pred = SQLiteMatchPredicate(dialect, table="docs", query='"web frameworks"')

# FTS5 spells NEAR as a function: NEAR(a b) or NEAR(a b, distance).
# The infix form "a NEAR b" is ts_query syntax and is not accepted here --
# it matches nothing rather than reporting a syntax error.
near_pred = SQLiteMatchPredicate(dialect, table="docs", query="NEAR(Python web)")

column_pred = SQLiteMatchPredicate(dialect, table="docs", query="python", columns=["title"])

boolean_pred = SQLiteMatchPredicate(dialect, table="docs", query="Python NOT Django")


def execute_match_query(pred: SQLiteMatchPredicate) -> list:
    """Build and execute a FTS5 MATCH query using QueryExpression."""
    query = QueryExpression(
        dialect=dialect,
        select=[WildcardExpression(dialect)],
        from_=TableExpression(dialect, "docs"),
        where=pred,
    )
    sql, params = query.to_sql()
    # StatementType.DQL is what makes execute() fetch and return rows. Without
    # it a SELECT returns result.data = None and every loop below iterates an
    # empty list -- the query runs and the example prints headers with nothing
    # under them.
    return backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DQL))


# Execute basic MATCH search
result = execute_match_query(match_pred)
print("\nBasic MATCH results (documents containing 'Python'):")
for row in result.data or []:
    print(f"  {row}")

# Execute prefix search
result = execute_match_query(prefix_pred)
print("\nPrefix search results (words starting with 'prog'):")
for row in result.data or []:
    print(f"  {row}")

# Execute phrase search
result = execute_match_query(phrase_pred)
print("\nPhrase search results (exact phrase 'web frameworks'):")
for row in result.data or []:
    print(f"  {row}")

# Execute NEAR query
result = execute_match_query(near_pred)
print("\nNEAR query results ('Python' near 'web'):")
for row in result.data or []:
    print(f"  {row}")

# Execute column-specific search
result = execute_match_query(column_pred)
print("\nColumn-specific search results ('Python' in title only):")
for row in result.data or []:
    print(f"  {row}")

# Execute boolean query
result = execute_match_query(boolean_pred)
print("\nBoolean query results ('Python NOT Django'):")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
