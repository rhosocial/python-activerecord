"""
Subquery in WHERE clause and FROM clause.
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
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)
""")
backend.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department_id INTEGER,
    salary REAL,
    FOREIGN KEY (department_id) REFERENCES departments(id)
)
""")
backend.execute("INSERT INTO departments (name) VALUES ('Engineering')")
backend.execute("INSERT INTO departments (name) VALUES ('Sales')")
backend.execute("INSERT INTO employees (name, department_id, salary) VALUES ('Alice', 1, 100000)")
backend.execute("INSERT INTO employees (name, department_id, salary) VALUES ('Bob', 1, 80000)")
backend.execute("INSERT INTO employees (name, department_id, salary) VALUES ('Charlie', 2, 90000)")

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    Column,
    WhereClause,
)
from rhosocial.activerecord.backend.expression.core import Subquery, Literal, FunctionCall
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

# Subquery in WHERE clause: find employees with salary above average
avg_salary_subquery = QueryExpression(
    dialect=dialect,
    select=[FunctionCall(dialect, 'AVG', Column(dialect, 'salary'))],
    from_=TableExpression(dialect, 'employees'),
)

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'name'),
        Column(dialect, 'salary'),
    ],
    from_=TableExpression(dialect, 'employees'),
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            '>',
            Column(dialect, 'salary'),
            Subquery(dialect, avg_salary_subquery),
        ),
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
