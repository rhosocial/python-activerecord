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
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
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
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect


# Version-gated features (RETURNING, JSON1, math functions) read the
# dialect version, which is only known after the server is inspected.
backend.introspect_and_adapt()
create_table = CreateTableExpression(
    dialect=dialect,
    table="users",
    columns=[
        ColumnDefinition(dialect, 
            "id",
            IntegerType(dialect),
            constraints=[
                ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY),
                ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL, is_auto_increment=True),
            ],
        ),
        ColumnDefinition(dialect, 
            "name",
            TextType(dialect),
            constraints=[
                ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
            ],
        ),
        ColumnDefinition(dialect, "email", TextType(dialect)),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

create_index = CreateIndexExpression(
    dialect=dialect,
    index_name="idx_users_email",
    table_name="users",
    columns=["email"],
    if_not_exists=True,
)
sql, params = create_index.to_sql()
backend.execute(sql, params)

users = [
    ("Alice", "alice@example.com"),
    ("Bob", "bob@example.com"),
    ("Charlie", "charlie@example.com"),
]
for name, email in users:
    insert_expr = InsertExpression(
        dialect=dialect,
        into="users",
        columns=["name", "email"],
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
    select=[Column(dialect, "*")],
    from_=TableExpression(dialect, "users"),
    where=ComparisonPredicate(
        dialect,
        "=",
        Column(dialect, "name"),
        Literal(dialect, "Alice"),
    ),
)
# Use backend.explain() rather than rendering EXPLAIN yourself and running it
# through backend.execute(). EXPLAIN output does not come back as rows on the
# normal QueryResult -- result.data is None -- so the plan has to be read from
# the dedicated result type.
print("1. Table SCAN (no index on name):")
plan = backend.explain(query1, ExplainOptions(type=ExplainType.QUERY_PLAN))
print(f"SQL: {plan.sql}")
for row in plan.rows:
    print(f"  {row.detail}")
print(f"  full scan: {plan.is_full_scan}, index used: {plan.is_index_used}")

# 2. EXPLAIN QUERY PLAN for index search (email has index)
query2 = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, "*")],
    from_=TableExpression(dialect, "users"),
    where=ComparisonPredicate(
        dialect,
        "=",
        Column(dialect, "email"),
        Literal(dialect, "alice@example.com"),
    ),
)
print("\n2. Index SEARCH (using idx_users_email):")
plan = backend.explain(query2, ExplainOptions(type=ExplainType.QUERY_PLAN))
print(f"SQL: {plan.sql}")
for row in plan.rows:
    print(f"  {row.detail}")
print(f"  full scan: {plan.is_full_scan}, index used: {plan.is_index_used}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Call backend.explain(expr, ExplainOptions(type=ExplainType.QUERY_PLAN));
#    do not render EXPLAIN and run it through backend.execute(), which returns
#    no rows for it
# 2. "SCAN" = full table scan, "SEARCH" = index used
# 3. "USING INDEX" shows which index is being used
# 4. Query plan helps identify performance bottlenecks
