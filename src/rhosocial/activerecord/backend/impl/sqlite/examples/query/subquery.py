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

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
    DropTableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    TableConstraint,
    TableConstraintType,
)

departments_table = CreateTableExpression(
    dialect=dialect,
    table_name='departments',
    columns=[
        ColumnDefinition('id', 'INTEGER', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('name', 'TEXT', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
    ],
    if_not_exists=True,
)
sql, params = departments_table.to_sql()
backend.execute(sql, params)

employees_table = CreateTableExpression(
    dialect=dialect,
    table_name='employees',
    columns=[
        ColumnDefinition('id', 'INTEGER', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('name', 'TEXT', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
        ColumnDefinition('department_id', 'INTEGER'),
        ColumnDefinition('salary', 'REAL'),
    ],
    table_constraints=[
        TableConstraint(
            constraint_type=TableConstraintType.FOREIGN_KEY,
            columns=['department_id'],
            foreign_key_table='departments',
            foreign_key_columns=['id'],
        ),
    ],
    if_not_exists=True,
)
sql, params = employees_table.to_sql()
backend.execute(sql, params)

departments = [('Engineering',), ('Sales',)]
for dept in departments:
    insert_expr = InsertExpression(
        dialect=dialect,
        into='departments',
        columns=['name'],
        source=ValuesSource(dialect, [[Literal(dialect, v) for v in dept]]),
    )
    sql, params = insert_expr.to_sql()
    backend.execute(sql, params)

employees = [
    ('Alice', 1, 100000),
    ('Bob', 1, 80000),
    ('Charlie', 2, 90000),
]
for emp in employees:
    insert_expr = InsertExpression(
        dialect=dialect,
        into='employees',
        columns=['name', 'department_id', 'salary'],
        source=ValuesSource(dialect, [[Literal(dialect, v) for v in emp]]),
    )
    sql, params = insert_expr.to_sql()
    backend.execute(sql, params)

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
