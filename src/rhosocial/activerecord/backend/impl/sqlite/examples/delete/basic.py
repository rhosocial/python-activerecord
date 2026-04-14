"""
Delete records and return affected row count.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

# Create table and insert test data
backend.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
""")
backend.execute("INSERT INTO users (name) VALUES ('Alice')")

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    DeleteExpression,
    ReturningClause,
    TableExpression,
    Column,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

delete_expr = DeleteExpression(
    dialect=dialect,
    table=TableExpression(dialect, 'users'),
    where=ComparisonPredicate(
        dialect,
        '=',
        Column(dialect, 'name'),
        Literal(dialect, 'Alice'),
    ),
    returning=ReturningClause(dialect, [Column(dialect, 'id')]),
    dialect_options={},
)

sql, params = delete_expr.to_sql()
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