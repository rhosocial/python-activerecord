"""
SQLite transaction modes.

This example demonstrates:
1. DEFERRED and IMMEDIATE transaction behavior via transaction manager settings
2. EXCLUSIVE transaction mode via BeginTransactionExpression.begin_type()
3. Nested transactions with automatic savepoints
4. WAL mode for better concurrency
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    DropTableExpression,
    InsertExpression,
    QueryExpression,
    TableExpression,
    UpdateExpression,
    ValuesSource,
    WhereClause,
)
from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
)
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.transaction import IsolationLevel

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
backend.connect()
dialect = backend.dialect

dql_options = ExecutionOptions(stmt_type=StatementType.DQL)
ddl_options = ExecutionOptions(stmt_type=StatementType.DDL)


def execute_expression(expression, options=None):
    sql, params = expression.to_sql()
    print(f"SQL: {sql}")
    print(f"Params: {params}")
    return backend.execute(sql, params, options=options)


def update_balance(name, amount):
    return UpdateExpression(
        dialect=dialect,
        table='accounts',
        assignments={
            'balance': Literal(dialect, amount),
        },
        where=WhereClause(
            dialect,
            condition=ComparisonPredicate(
                dialect,
                '=',
                Column(dialect, 'name'),
                Literal(dialect, name),
            ),
        ),
    )


def fetch_balances():
    query = QueryExpression(
        dialect=dialect,
        select=[Column(dialect, 'name'), Column(dialect, 'balance')],
        from_=TableExpression(dialect, 'accounts'),
    )
    return execute_expression(query, dql_options).data


create_table = CreateTableExpression(
    dialect=dialect,
    table_name='accounts',
    columns=[
        ColumnDefinition(
            'id',
            'INTEGER',
            constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
        ),
        ColumnDefinition(
            'name',
            'TEXT',
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)],
        ),
        ColumnDefinition('balance', 'REAL'),
    ],
    if_not_exists=True,
)
execute_expression(create_table, ddl_options)

insert = InsertExpression(
    dialect=dialect,
    into='accounts',
    columns=['name', 'balance'],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 'Alice'), Literal(dialect, 1000)],
            [Literal(dialect, 'Bob'), Literal(dialect, 500)],
        ],
    ),
)
execute_expression(insert)

# ============================================================
# SECTION: Transaction Modes
# ============================================================
backend.transaction_manager.isolation_level = IsolationLevel.READ_UNCOMMITTED
with backend.transaction():
    execute_expression(update_balance('Alice', 900))
print(f"After DEFERRED-style transaction: {fetch_balances()}")

backend.transaction_manager.isolation_level = IsolationLevel.SERIALIZABLE
with backend.transaction():
    execute_expression(update_balance('Bob', 450))
print(f"After IMMEDIATE transaction: {fetch_balances()}")

# ============================================================
# SECTION: EXCLUSIVE Transaction Mode
# ============================================================
# Use begin_type to explicitly control SQLite's BEGIN mode.
# This is different from PRAGMA locking_mode:
# - BEGIN EXCLUSIVE: exclusive lock only for this transaction
# - PRAGMA locking_mode=EXCLUSIVE: persistent lock across all transactions
from rhosocial.activerecord.backend.expression.transaction import BeginTransactionExpression

exclusive_begin = BeginTransactionExpression(dialect).begin_type("EXCLUSIVE")
sql, params = exclusive_begin.to_sql()
print(f"EXCLUSIVE BEGIN SQL: {sql}")

backend.transaction_manager.begin_type = "EXCLUSIVE"
with backend.transaction():
    execute_expression(update_balance('Alice', 880))
print(f"After EXCLUSIVE transaction: {fetch_balances()}")

# Reset to default (isolation level-based mapping)
backend.transaction_manager.begin_type = None

# ============================================================
# SECTION: SAVEPOINT for Nested Transactions
# ============================================================
with backend.transaction():
    execute_expression(update_balance('Alice', 870))
    try:
        with backend.transaction():
            execute_expression(update_balance('Alice', 850))
            raise RuntimeError('rollback inner transaction')
    except RuntimeError as error:
        print(f"Nested transaction rolled back: {error}")

print(f"After nested transaction: {fetch_balances()}")

# ============================================================
# SECTION: WAL Mode
# ============================================================
backend.introspector.pragma.set("journal_mode", "WAL")
journal_mode = backend.introspector.pragma.get("journal_mode")
print(f"Journal mode: {journal_mode}")

# ============================================================
# SECTION: Teardown
# ============================================================
drop_table = DropTableExpression(dialect=dialect, table_name='accounts', if_exists=True)
execute_expression(drop_table, ddl_options)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. READ_UNCOMMITTED maps to SQLite's DEFERRED transaction behavior
# 2. SERIALIZABLE maps to SQLite's IMMEDIATE transaction behavior
# 3. Use BeginTransactionExpression.begin_type("EXCLUSIVE") for exclusive transactions
# 4. Or set transaction_manager.begin_type = "EXCLUSIVE" for all subsequent transactions
# 5. Nested backend.transaction() calls use savepoints automatically
# 6. WAL mode improves concurrent read/write behavior
