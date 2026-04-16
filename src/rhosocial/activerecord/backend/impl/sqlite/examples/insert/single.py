"""
Single Row INSERT - SQLite.

This example demonstrates:
1. INSERT single row
2. INSERT with auto-increment
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
    table_name='users',
    columns=[
        ColumnDefinition('id', 'INTEGER', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('name', 'TEXT'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: Single INSERT (using InsertExpression)
# ============================================================
from rhosocial.activerecord.backend.expression import InsertExpression, ValuesSource

insert_expr = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['name'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 'Alice')],
    ]),
)
sql, params = insert_expr.to_sql()
print(f"Insert SQL: {sql}")
print(f"Params: {params}")
backend.execute(sql, params)

result = backend.execute("SELECT * FROM users")
print(f"Result: {result.data}")

# ============================================================
# SECTION: Teardown
# ============================================================
drop_expr = DropTableExpression(dialect=dialect, table_name='users', if_exists=True)
sql, params = drop_expr.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use InsertExpression with ValuesSource for single row
# 2. Auto-increment uses PRIMARY KEY constraint