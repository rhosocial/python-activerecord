"""
Basic SELECT query with WHERE, ORDER BY, and LIMIT clauses.
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
    age INTEGER,
    status TEXT DEFAULT 'active'
)
""")
backend.execute("INSERT INTO users (name, age, status) VALUES ('Alice', 30, 'active')")
backend.execute("INSERT INTO users (name, age, status) VALUES ('Bob', 25, 'active')")
backend.execute("INSERT INTO users (name, age, status) VALUES ('Charlie', 35, 'inactive')")

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
    WhereClause,
    OrderByClause,
    LimitOffsetClause,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'name'),
        Column(dialect, 'age'),
    ],
    from_=TableExpression(dialect, 'users'),
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            '=',
            Column(dialect, 'status'),
            Literal(dialect, 'active'),
        ),
    ),
    order_by=OrderByClause(
        dialect,
        expressions=[(Column(dialect, 'age'), 'ASC')],
    ),
    limit_offset=LimitOffsetClause(dialect, limit=10),
)

sql, params = query.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute(sql, params, options=options)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
