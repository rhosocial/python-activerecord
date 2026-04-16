"""
SQLite Transaction Modes.

This example demonstrates:
1. DEFERRED, IMMEDIATE, EXCLUSIVE transaction modes
2. SQLite's limited row locking (database-level)
3. Using SAVEPOINT for nested transactions
4. Isolation levels
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
    DropTableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='accounts',
    columns=[
        ColumnDefinition('id', 'INTEGER', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
        ]),
        ColumnDefinition('name', 'TEXT', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
        ColumnDefinition('balance', 'REAL'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    into='accounts',
    columns=['name', 'balance'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 'Alice'), Literal(dialect, 1000)],
        [Literal(dialect, 'Bob'), Literal(dialect, 500)],
    ]),
)
sql, params = insert.to_sql()
print(f"Insert SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: Transaction Modes
# ============================================================
# SQLite has three transaction modes:
# - DEFERRED: Default, acquires lock when needed
# - IMMEDIATE: Acquires RESERVED lock immediately
# - EXCLUSIVE: Acquires EXCLUSIVE lock immediately

# IMMEDIATE transaction - good for write-heavy workloads
# Start a transaction with IMMEDIATE mode
backend.execute("BEGIN IMMEDIATE")

# Now we can do operations
backend.execute("UPDATE accounts SET balance = balance - 100 WHERE name = 'Alice'")

# Commit
backend.execute("COMMIT")

# ============================================================
# SECTION: EXCLUSIVE Transaction
# ============================================================
# EXCLUSIVE mode blocks other writes completely

backend.execute("BEGIN EXCLUSIVE")
backend.execute("UPDATE accounts SET balance = balance - 50 WHERE name = 'Bob'")
backend.execute("COMMIT")

# ============================================================
# SECTION: SAVEPOINT for Nested Transactions
# ============================================================
# SQLite supports SAVEPOINT for nested transactions

# Start a transaction
backend.execute("BEGIN")

# Make a change
backend.execute("UPDATE accounts SET balance = balance - 10 WHERE name = 'Alice'")

# Create a savepoint
backend.execute("SAVEPOINT sp1")

# Make another change
backend.execute("UPDATE accounts SET balance = balance - 20 WHERE name = 'Alice'")

# Rollback to savepoint (keep changes before sp1)
backend.execute("ROLLBACK TO SAVEPOINT sp1")

# Release savepoint
backend.execute("RELEASE SAVEPOINT sp1")

# Commit outer transaction
backend.execute("COMMIT")

# ============================================================
# SECTION: Isolation Notes
# ============================================================
# SQLite uses database-level locking, not row-level:
# - Readers don't block writers
# - Writers block other writers
# - Use write-ahead logging (WAL) mode for better concurrency

# Switch to WAL mode for better concurrency
backend.execute("PRAGMA journal_mode=WAL")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. SQLite has DEFERRED, IMMEDIATE, EXCLUSIVE modes
# 2. No row-level locking - database-level only
# 3. Use SAVEPOINT for nested transactions
# 4. IMMEDIATE/EXCLUSIVE acquire locks sooner
# 5. WAL mode improves concurrent reads
# 6. FOR UPDATE is not supported