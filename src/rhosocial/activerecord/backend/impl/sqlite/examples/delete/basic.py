"""
Delete records and return affected row count.
"""
META = {
    'title': 'Delete with RETURNING',
    'dialect_protocols': ['ReturningSupport'],
    'priority': 10,
}

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.expression import (
    DeleteExpression,
    ReturningClause,
    TableExpression,
    Column,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

# Setup: create table and insert test data
config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

backend.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
""")
backend.execute("INSERT INTO users (name) VALUES ('Alice')")

# Build DELETE expression
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

# Execute
result = backend.execute(sql, params)
print(f"Affected rows: {result.affected_rows}")

backend.disconnect()