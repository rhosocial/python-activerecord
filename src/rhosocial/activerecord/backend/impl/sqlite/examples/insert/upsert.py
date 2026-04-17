"""
UPSERT (INSERT OR REPLACE / INSERT OR IGNORE) - SQLite.

This example demonstrates:
1. INSERT OR REPLACE - replaces existing row on conflict
2. INSERT OR IGNORE - silently ignores rows that would cause conflict
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import (
    InsertExpression,
    ValuesSource,
    QueryExpression,
    TableExpression,
    CreateTableExpression,
    DropTableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal, WildcardExpression
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='users',
    columns=[
        ColumnDefinition('id', 'INTEGER', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('username', 'TEXT', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
            ColumnConstraint(ColumnConstraintType.UNIQUE),
        ]),
        ColumnDefinition('email', 'TEXT', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
        ColumnDefinition('login_count', 'INTEGER'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

# Insert initial data
insert_initial = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['username', 'email', 'login_count'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 'alice'), Literal(dialect, 'alice@example.com'), Literal(dialect, 5)],
        [Literal(dialect, 'bob'), Literal(dialect, 'bob@example.com'), Literal(dialect, 3)],
    ]),
)
sql, params = insert_initial.to_sql()
backend.execute(sql, params)

# Verify initial data
verify_query = QueryExpression(
    dialect=dialect,
    select=[WildcardExpression(dialect)],
    from_=TableExpression(dialect, 'users'),
)
options = ExecutionOptions(stmt_type=StatementType.DQL)
sql, params = verify_query.to_sql()
result = backend.execute(sql, params, options=options)
print("Initial data:")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

# --- INSERT OR REPLACE ---
# INSERT OR REPLACE deletes the existing conflicting row and inserts the new one.
# Note: This resets any columns NOT provided in the insert to their defaults.
# Use dialect_options={'or_replace': True} to enable this SQLite-specific syntax.
insert_or_replace = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['username', 'email', 'login_count'],
    source=ValuesSource(dialect, [
        # 'alice' already exists with id=1; OR REPLACE will delete old row and insert new one
        [Literal(dialect, 'alice'), Literal(dialect, 'alice_new@example.com'), Literal(dialect, 0)],
    ]),
    dialect_options={'or_replace': True},
)
sql, params = insert_or_replace.to_sql()
print(f"\nINSERT OR REPLACE SQL: {sql}")
print(f"Params: {params}")

# --- INSERT OR IGNORE ---
# INSERT OR IGNORE silently skips rows that would cause constraint violations.
# Use dialect_options={'or_ignore': True} to enable this SQLite-specific syntax.
insert_or_ignore = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['username', 'email', 'login_count'],
    source=ValuesSource(dialect, [
        # 'bob' already exists; OR IGNORE will skip this row
        [Literal(dialect, 'bob'), Literal(dialect, 'bob_new@example.com'), Literal(dialect, 10)],
        # 'charlie' does not exist; this row will be inserted normally
        [Literal(dialect, 'charlie'), Literal(dialect, 'charlie@example.com'), Literal(dialect, 1)],
    ]),
    dialect_options={'or_ignore': True},
)
sql, params = insert_or_ignore.to_sql()
print(f"\nINSERT OR IGNORE SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================

# Execute INSERT OR REPLACE
sql, params = insert_or_replace.to_sql()
result = backend.execute(sql, params)
print(f"\nINSERT OR REPLACE affected rows: {result.affected_rows}")

# Verify after INSERT OR REPLACE: alice's id changed (old row deleted, new row inserted)
sql, params = verify_query.to_sql()
result = backend.execute(sql, params, options=options)
print("After INSERT OR REPLACE:")
for row in result.data or []:
    print(f"  {row}")

# Execute INSERT OR IGNORE
sql, params = insert_or_ignore.to_sql()
result = backend.execute(sql, params)
print(f"\nINSERT OR IGNORE affected rows: {result.affected_rows}")

# Verify after INSERT OR IGNORE: bob unchanged, charlie added
sql, params = verify_query.to_sql()
result = backend.execute(sql, params, options=options)
print("After INSERT OR IGNORE:")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
drop_expr = DropTableExpression(dialect=dialect, table_name='users', if_exists=True)
sql, params = drop_expr.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use dialect_options={'or_replace': True} for INSERT OR REPLACE
#    - Deletes existing row on conflict and inserts new row
#    - Auto-increment ID and unspecified columns are reset to defaults
# 2. Use dialect_options={'or_ignore': True} for INSERT OR IGNORE
#    - Silently skips rows that would cause UNIQUE/PRIMARY KEY constraint violations
#    - Other rows in the same batch are still inserted
# 3. Cannot combine or_replace/or_ignore with on_conflict (OnConflictClause)
#    - Use either SQLite-specific OR syntax OR standard ON CONFLICT, not both
