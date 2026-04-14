"""
Batch insert with multiple rows.
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

backend.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT
)
""")

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    InsertExpression,
    ValuesSource,
    TableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal

insert_expr = InsertExpression(
    dialect=dialect,
    into=TableExpression(dialect, 'users'),
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 'Alice'), Literal(dialect, 'alice@example.com')],
            [Literal(dialect, 'Bob'), Literal(dialect, 'bob@example.com')],
            [Literal(dialect, 'Charlie'), Literal(dialect, 'charlie@example.com')],
        ],
    ),
    columns=['name', 'email'],
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

# Verify
options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute("SELECT * FROM users", options=options)
print(f"Total rows in table: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
