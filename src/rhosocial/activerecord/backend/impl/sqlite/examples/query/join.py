"""
JOIN query with multiple tables.
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
    name TEXT NOT NULL
)
""")
backend.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")
backend.execute("INSERT INTO users (name) VALUES ('Alice')")
backend.execute("INSERT INTO users (name) VALUES ('Bob')")
backend.execute("INSERT INTO orders (user_id, amount) VALUES (1, 100.0)")
backend.execute("INSERT INTO orders (user_id, amount) VALUES (1, 200.0)")
backend.execute("INSERT INTO orders (user_id, amount) VALUES (2, 150.0)")

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
    JoinExpression,
)
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

join_expr = JoinExpression(
    dialect=dialect,
    left_table=TableExpression(dialect, 'users', alias='u'),
    right_table=TableExpression(dialect, 'orders', alias='o'),
    join_type='LEFT JOIN',
    condition=ComparisonPredicate(
        dialect,
        '=',
        Column(dialect, 'id', 'u'),
        Column(dialect, 'user_id', 'o'),
    ),
)

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'name', 'u'),
        Column(dialect, 'amount', 'o'),
    ],
    from_=join_expr,
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
