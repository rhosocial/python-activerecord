"""
Complex predicates: LIKE, IN, BETWEEN, IS NULL.
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
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL,
    category TEXT,
    description TEXT
)
""")
backend.execute("INSERT INTO products (name, price, category, description) VALUES ('Apple', 1.5, 'Fruit', 'Fresh red apple')")
backend.execute("INSERT INTO products (name, price, category, description) VALUES ('Banana', 0.8, 'Fruit', NULL)")
backend.execute("INSERT INTO products (name, price, category, description) VALUES ('Carrot', 0.5, 'Vegetable', 'Organic carrot')")
backend.execute("INSERT INTO products (name, price, category, description) VALUES ('Orange', 2.0, 'Fruit', 'Sweet orange')")
backend.execute("INSERT INTO products (name, price, category, description) VALUES ('Broccoli', 1.2, 'Vegetable', NULL)")

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
    WhereClause,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.predicates import (
    LikePredicate,
    InPredicate,
    BetweenPredicate,
    IsNullPredicate,
    LogicalPredicate,
)

# Combine multiple predicates: (LIKE pattern) AND (IN list) AND (BETWEEN range) AND (IS NOT NULL)
like_pred = LikePredicate(dialect, 'LIKE', Column(dialect, 'name'), Literal(dialect, '%a%'))
in_pred = InPredicate(dialect, Column(dialect, 'category'), Literal(dialect, ('Fruit', 'Vegetable')))
between_pred = BetweenPredicate(dialect, Column(dialect, 'price'), Literal(dialect, 0.5), Literal(dialect, 2.0))
not_null_pred = IsNullPredicate(dialect, Column(dialect, 'description'), is_not=True)

combined_pred = LogicalPredicate(dialect, 'AND', like_pred, in_pred, between_pred, not_null_pred)

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'name'),
        Column(dialect, 'price'),
        Column(dialect, 'category'),
    ],
    from_=TableExpression(dialect, 'products'),
    where=WhereClause(dialect, condition=combined_pred),
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
