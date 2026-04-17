"""
EXPLAIN and Query Plan analysis - SQLite.

This example demonstrates:
1. Using EXPLAIN QUERY PLAN to analyze query execution
2. Understanding scan types (SCAN vs SEARCH)
3. Index usage analysis
4. Interpreting query plan output
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
    QueryExpression,
    TableExpression,
    ExplainExpression,
    CreateIndexExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal, Column
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.statements.explain import ExplainType, ExplainOptions
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='users',
    columns=[
        ColumnDefinition('id', 'INTEGER', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('name', 'TEXT', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
        ColumnDefinition('email', 'TEXT'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

create_index = CreateIndexExpression(
    dialect=dialect,
    index_name='idx_users_email',
    table_name='users',
    columns=['email'],
    if_not_exists=True,
)
sql, params = create_index.to_sql()
backend.execute(sql, params)

users = [
    ('Alice', 'alice@example.com'),
    ('Bob', 'bob@example.com'),
    ('Charlie', 'charlie@example.com'),
]
for name, email in users:
    insert_expr = InsertExpression(
        dialect=dialect,
        into='users',
        columns=['name', 'email'],
        source=ValuesSource(dialect, [[Literal(dialect, name), Literal(dialect, email)]]),
    )
    sql, params = insert_expr.to_sql()
    backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

# 1. EXPLAIN QUERY PLAN for table scan (no index on name column)
query1 = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, '*')],
    from_=TableExpression(dialect, 'users'),
    where=ComparisonPredicate(
        dialect, '=', Column(dialect, 'name'), Literal(dialect, 'Alice'),
    ),
)
explain_scan = ExplainExpression(
    dialect=dialect,
    statement=query1,
    options=ExplainOptions(type=ExplainType.QUERY_PLAN),
)
sql, params = explain_scan.to_sql()
print("1. Table SCAN (no index on name):")
print(f"SQL: {sql}")
result = backend.execute(sql, params)
for row in result.data:
    print(f"  {row}")

# 2. EXPLAIN QUERY PLAN for index search (email has index)
query2 = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, '*')],
    from_=TableExpression(dialect, 'users'),
    where=ComparisonPredicate(
        dialect, '=', Column(dialect, 'email'), Literal(dialect, 'alice@example.com'),
    ),
)
explain_search = ExplainExpression(
    dialect=dialect,
    statement=query2,
    options=ExplainOptions(type=ExplainType.QUERY_PLAN),
)
sql, params = explain_search.to_sql()
print("\n2. Index SEARCH (using idx_users_email):")
print(f"SQL: {sql}")
result = backend.execute(sql, params)
for row in result.data:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use ExplainType.QUERY_PLAN for SQLite query plan analysis
# 2. "SCAN" = full table scan, "SEARCH" = index used
# 3. "USING INDEX" shows which index is being used
# 4. Query plan helps identify performance bottlenecks