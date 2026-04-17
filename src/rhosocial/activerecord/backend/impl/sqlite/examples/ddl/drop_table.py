"""
DROP TABLE - SQLite.

This example demonstrates:
1. DROP TABLE
2. DROP TABLE IF EXISTS
"""

# ============================================================
# SECTION: Setup
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import CreateTableExpression
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='users',
    columns=[
        ColumnDefinition('id', 'INTEGER'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: DROP TABLE (using DropTableExpression)
# ============================================================
from rhosocial.activerecord.backend.expression import DropTableExpression

drop_expr = DropTableExpression(
    dialect=dialect,
    table_name='users',
)
sql, params = drop_expr.to_sql()
print(f"DROP TABLE SQL: {sql}")
print(f"Params: {params}")
backend.execute(sql, params)

# Already deleted, use IF EXISTS
drop_expr_exists = DropTableExpression(
    dialect=dialect,
    table_name='users',
    if_exists=True,
)
sql, params = drop_expr_exists.to_sql()
print(f"DROP TABLE IF EXISTS SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: Summary
# ============================================================
backend.disconnect()

# Key points:
# 1. Use DropTableExpression to drop tables
# 2. if_exists=True prevents error if missing