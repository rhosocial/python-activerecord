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
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.expression import (
    Column,
    InsertExpression,
    ValuesSource,
    QueryExpression,
    TableExpression,
    WildcardExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.impl.sqlite.expression import SQLiteMatchPredicate

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
# SQLiteMatchPredicate delegates to the SQLite dialect's FTS5 formatting.
match_pred = SQLiteMatchPredicate(dialect, table='docs', query='Python')

prefix_pred = SQLiteMatchPredicate(dialect, table='docs', query='prog*')

phrase_pred = SQLiteMatchPredicate(dialect, table='docs', query='"web frameworks"')

near_pred = SQLiteMatchPredicate(dialect, table='docs', query='Python NEAR web')

column_pred = SQLiteMatchPredicate(
    dialect,
    table='docs',
    query='python',
    columns=['title']
)

boolean_pred = SQLiteMatchPredicate(dialect, table='docs', query='Python NOT Django')


def execute_match_query(pred: SQLiteMatchPredicate) -> list:
    """Build and execute a FTS5 MATCH query using QueryExpression."""
    query = QueryExpression(
        dialect=dialect,
        select=[WildcardExpression(dialect)],
        from_=TableExpression(dialect, 'docs'),
        where=pred,
    )
    sql, params = query.to_sql()
    return backend.execute(sql, params, options=options)


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
