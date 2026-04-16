"""
FOR UPDATE row locking with SQLite limitations.

This example demonstrates:
1. ForUpdateClause construction for SELECT ... FOR UPDATE
2. SQLite does NOT support FOR UPDATE - supports_for_update() returns False
3. The proper SQLite alternative: BEGIN IMMEDIATE / EXCLUSIVE transactions
4. How to check dialect capability before using FOR UPDATE
"""

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    CreateTableExpression,
    DropTableExpression,
    InsertExpression,
    ValuesSource,
    UpdateExpression,
    WhereClause,
)
from rhosocial.activerecord.backend.expression.core import Literal, Column
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.query_parts import ForUpdateClause
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.transaction import BeginTransactionExpression
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
backend.connect()
dialect = backend.dialect

dql_options = ExecutionOptions(stmt_type=StatementType.DQL)
ddl_options = ExecutionOptions(stmt_type=StatementType.DDL)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name="accounts",
    columns=[
        ColumnDefinition(
            "id",
            "INTEGER",
            constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
        ),
        ColumnDefinition(
            "name",
            "TEXT",
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)],
        ),
        ColumnDefinition("balance", "REAL"),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params, options=ddl_options)

insert = InsertExpression(
    dialect=dialect,
    into="accounts",
    columns=["name", "balance"],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, "Alice"), Literal(dialect, 1000)],
            [Literal(dialect, "Bob"), Literal(dialect, 500)],
        ],
    ),
)
sql, params = insert.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

# --- 1. ForUpdateClause construction ---
# Even though SQLite does not support FOR UPDATE, you can still construct
# the clause object. This is useful for code that targets multiple backends.

# Basic FOR UPDATE
for_update_basic = ForUpdateClause(dialect)
sql, params = for_update_basic.to_sql()
print(f"Basic FOR UPDATE SQL: {sql}")

# FOR UPDATE with OF columns
for_update_of = ForUpdateClause(
    dialect,
    of_columns=[Column(dialect, "id"), "balance"],
)
sql, params = for_update_of.to_sql()
print(f"FOR UPDATE OF SQL: {sql}")

# FOR UPDATE with NOWAIT
for_update_nowait = ForUpdateClause(dialect, nowait=True)
sql, params = for_update_nowait.to_sql()
print(f"FOR UPDATE NOWAIT SQL: {sql}")

# --- 2. Check SQLite's FOR UPDATE support ---
# SQLite uses database-level locking (SHARED, RESERVED, PENDING, EXCLUSIVE)
# rather than row-level locking. Therefore supports_for_update() returns False.
print(f"SQLite supports FOR UPDATE: {dialect.supports_for_update()}")
print(f"SQLite supports FOR UPDATE SKIP LOCKED: {dialect.supports_for_update_skip_locked()}")

# --- 3. Using ForUpdateClause in QueryExpression raises UnsupportedFeatureError ---
# When you include for_update in a QueryExpression, the dialect check
# will raise UnsupportedFeatureError at SQL generation time.
query_with_for_update = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, "name"), Column(dialect, "balance")],
    from_=TableExpression(dialect, "accounts"),
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            "=",
            Column(dialect, "name"),
            Literal(dialect, "Alice"),
        ),
    ),
    for_update=ForUpdateClause(dialect),
)
try:
    sql, params = query_with_for_update.to_sql()
except UnsupportedFeatureError as e:
    print(f"UnsupportedFeatureError: {e}")

# --- 4. SQLite alternative: BEGIN IMMEDIATE / EXCLUSIVE transactions ---
# For write serialization in SQLite, use BEGIN IMMEDIATE or BEGIN EXCLUSIVE
# instead of FOR UPDATE. These acquire a RESERVED or EXCLUSIVE lock at
# transaction start, preventing other writers.

# BEGIN IMMEDIATE: acquires RESERVED lock (allows readers, blocks writers)
immediate_begin = BeginTransactionExpression(dialect).begin_type("IMMEDIATE")
sql, params = immediate_begin.to_sql()
print(f"BEGIN IMMEDIATE SQL: {sql}")

# BEGIN EXCLUSIVE: acquires EXCLUSIVE lock (blocks both readers and writers)
exclusive_begin = BeginTransactionExpression(dialect).begin_type("EXCLUSIVE")
sql, params = exclusive_begin.to_sql()
print(f"BEGIN EXCLUSIVE SQL: {sql}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================

# Pattern: Check dialect capability before using FOR UPDATE
if dialect.supports_for_update():
    # This branch runs on MySQL/PostgreSQL but NOT SQLite
    query = QueryExpression(
        dialect=dialect,
        select=[Column(dialect, "name"), Column(dialect, "balance")],
        from_=TableExpression(dialect, "accounts"),
        where=WhereClause(
            dialect,
            condition=ComparisonPredicate(
                dialect,
                "=",
                Column(dialect, "name"),
                Literal(dialect, "Alice"),
            ),
        ),
        for_update=ForUpdateClause(dialect),
    )
    sql, params = query.to_sql()
    print(f"SELECT ... FOR UPDATE SQL: {sql}")
else:
    # SQLite alternative: use IMMEDIATE transaction for write serialization
    print("SQLite: Using BEGIN IMMEDIATE instead of FOR UPDATE")
    backend.transaction_manager.begin_type = "IMMEDIATE"
    with backend.transaction():
        # Read within the transaction (RESERVED lock held)
        query = QueryExpression(
            dialect=dialect,
            select=[Column(dialect, "name"), Column(dialect, "balance")],
            from_=TableExpression(dialect, "accounts"),
            where=WhereClause(
                dialect,
                condition=ComparisonPredicate(
                    dialect,
                    "=",
                    Column(dialect, "name"),
                    Literal(dialect, "Alice"),
                ),
            ),
        )
        sql, params = query.to_sql()
        result = backend.execute(sql, params, options=dql_options)
        if result.data:
            print(f"  Read balance: {result.data[0]['balance']}")

        # Update within the same transaction
        update_expr = UpdateExpression(
            dialect=dialect,
            table="accounts",
            assignments={"balance": Literal(dialect, 950)},
            where=WhereClause(
                dialect,
                condition=ComparisonPredicate(
                    dialect,
                    "=",
                    Column(dialect, "name"),
                    Literal(dialect, "Alice"),
                ),
            ),
        )
        sql, params = update_expr.to_sql()
        backend.execute(sql, params)
    # Transaction committed, lock released

# Reset transaction manager to default
backend.transaction_manager.begin_type = None

# Verify the update
query = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, "name"), Column(dialect, "balance")],
    from_=TableExpression(dialect, "accounts"),
)
sql, params = query.to_sql()
result = backend.execute(sql, params, options=dql_options)
for row in result.data:
    print(f"  {row['name']}: {row['balance']}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_table = DropTableExpression(dialect=dialect, table_name="accounts", if_exists=True)
sql, params = drop_table.to_sql()
backend.execute(sql, params, options=ddl_options)
backend.disconnect()
