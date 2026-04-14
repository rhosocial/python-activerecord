"""
Insert a record and return the auto-generated ID using RETURNING clause.
"""
META = {
    'title': 'Insert with RETURNING',
    'dialect_protocols': ['ReturningSupport'],
    'priority': 10,
}

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.expression import (
    InsertExpression,
    ValuesSource,
    ReturningClause,
    TableExpression,
    Column,
)
from rhosocial.activerecord.backend.expression.core import Literal

# Get dialect
config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

# Check if RETURNING is supported
print(f"RETURNING supported: {dialect.supports_returning_clause()}")

# Build INSERT expression
insert_expr = InsertExpression(
    dialect=dialect,
    into=TableExpression(dialect, 'users'),
    source=ValuesSource(dialect, [[Literal(dialect, 'Alice')]]),
    columns=['name'],
    returning=ReturningClause(dialect, [Column(dialect, 'id')]),
    dialect_options={},
)

# Get SQL
sql, params = insert_expr.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

backend.disconnect()