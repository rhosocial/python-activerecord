"""
Aggregate query with GROUP BY and HAVING clauses.
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
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    status TEXT
)
""")
backend.execute("INSERT INTO orders (user_id, amount, status) VALUES (1, 100.0, 'completed')")
backend.execute("INSERT INTO orders (user_id, amount, status) VALUES (1, 200.0, 'completed')")
backend.execute("INSERT INTO orders (user_id, amount, status) VALUES (2, 150.0, 'completed')")
backend.execute("INSERT INTO orders (user_id, amount, status) VALUES (2, 50.0, 'pending')")
backend.execute("INSERT INTO orders (user_id, amount, status) VALUES (3, 300.0, 'completed')")

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
    GroupByHavingClause,
)
from rhosocial.activerecord.backend.expression.core import FunctionCall, Literal

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'user_id'),
        FunctionCall(dialect, 'SUM', Column(dialect, 'amount'), alias='total_amount'),
        FunctionCall(dialect, 'COUNT', Column(dialect, 'id'), alias='order_count'),
    ],
    from_=TableExpression(dialect, 'orders'),
    group_by_having=GroupByHavingClause(
        dialect,
        group_by=[Column(dialect, 'user_id')],
        having=FunctionCall(dialect, 'SUM', Column(dialect, 'amount')) > Literal(dialect, 100),
    ),
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
