"""
Insert a record and return the auto-generated ID using RETURNING clause.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

# Create table for testing
backend.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
""")

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    InsertExpression,
    ValuesSource,
    ReturningClause,
    TableExpression,
    Column,
)
from rhosocial.activerecord.backend.expression.core import Literal

insert_expr = InsertExpression(
    dialect=dialect,
    into=TableExpression(dialect, 'users'),
    source=ValuesSource(dialect, [[Literal(dialect, 'Alice')]]),
    columns=['name'],
    returning=ReturningClause(dialect, [Column(dialect, 'id')]),
    dialect_options={},
)

sql, params = insert_expr.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(sql, params)
print(f"Affected rows: {result.affected_rows}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()