"""
CTE (Common Table Expressions): basic and recursive.
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
    QueryExpression,
    TableExpression,
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.core import Literal, Column
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

create_table = CreateTableExpression(
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
        ColumnDefinition('manager_id', 'INTEGER'),
        ColumnDefinition('department', 'TEXT'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# CEO (no manager), two VPs, and three individual contributors
employees_data = [
    (None, 'Alice', 'Engineering'),      # id=1, CEO
    (1, 'Bob', 'Engineering'),           # id=2, reports to Alice
    (1, 'Carol', 'Sales'),               # id=3, reports to Alice
    (2, 'Dave', 'Engineering'),          # id=4, reports to Bob
    (2, 'Eve', 'Engineering'),           # id=5, reports to Bob
    (3, 'Frank', 'Sales'),               # id=6, reports to Carol
]
for manager_id, name, dept in employees_data:
    insert_expr = InsertExpression(
        dialect=dialect,
        into='employees',
        columns=['manager_id', 'name', 'department'],
        source=ValuesSource(dialect, [[Literal(dialect, manager_id), Literal(dialect, name), Literal(dialect, dept)]]),
    )
    sql, params = insert_expr.to_sql()
    backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    CTEExpression,
    WithQueryExpression,
    GroupByHavingClause,
)
from rhosocial.activerecord.backend.expression.core import FunctionCall

# --- Example 1: Basic CTE (WITH clause) ---
# Compute average salary per department, then filter departments above a threshold.
# (We use COUNT here as a stand-in aggregate on the employees table.)

dept_count_cte = CTEExpression(
    dialect=dialect,
    name='dept_counts',
    query=QueryExpression(
        dialect=dialect,
        select=[
            Column(dialect, 'department'),
            FunctionCall(dialect, 'COUNT', Column(dialect, 'id'), alias='headcount'),
        ],
        from_=TableExpression(dialect, 'employees'),
        group_by_having=GroupByHavingClause(
            dialect,
            group_by=[Column(dialect, 'department')],
        ),
    ),
)

basic_cte_query = WithQueryExpression(
    dialect=dialect,
    ctes=[dept_count_cte],
    main_query=QueryExpression(
        dialect=dialect,
        select=[
            Column(dialect, 'department'),
            Column(dialect, 'headcount'),
        ],
        from_=TableExpression(dialect, 'dept_counts'),
    ),
)

sql, params = basic_cte_query.to_sql()
print(f"Basic CTE SQL: {sql}")
print(f"Params: {params}")

# --- Example 2: Recursive CTE for hierarchical data (org chart) ---
from rhosocial.activerecord.backend.expression import SetOperationExpression
from rhosocial.activerecord.backend.expression.predicates import IsNullPredicate

# Base case: top-level employees (no manager)
# The CTE columns parameter defines column names, so we don't need AS aliases
base_query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        Column(dialect, 'name'),
        Column(dialect, 'manager_id'),
        Column(dialect, 'department'),
        Literal(dialect, 0),
    ],
    from_=TableExpression(dialect, 'employees'),
    where=IsNullPredicate(dialect, Column(dialect, 'manager_id')),
)

# Recursive case: employees whose manager is already in org_chart
# Use a JOIN between the CTE result and employees table
from rhosocial.activerecord.backend.expression import JoinExpression
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate

join_expr = JoinExpression(
    dialect=dialect,
    left_table=TableExpression(dialect, 'org_chart', alias='oc'),
    right_table=TableExpression(dialect, 'employees', alias='e'),
    join_type='INNER JOIN',
    condition=ComparisonPredicate(dialect, '=', Column(dialect, 'id', 'oc'), Column(dialect, 'manager_id', 'e')),
)

recursive_query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id', 'e'),
        Column(dialect, 'name', 'e'),
        Column(dialect, 'manager_id', 'e'),
        Column(dialect, 'department', 'e'),
        Column(dialect, 'level', 'oc') + Literal(dialect, 1),
    ],
    from_=join_expr,
)

# Combine base and recursive with UNION ALL
union_all = SetOperationExpression(
    dialect=dialect,
    left=base_query,
    right=recursive_query,
    operation='UNION ALL',
)

# Wrap in a CTE and a WITH query
# The columns parameter assigns names to CTE result columns
org_chart_cte = CTEExpression(
    dialect=dialect,
    name='org_chart',
    query=union_all,
    columns=['id', 'name', 'manager_id', 'department', 'level'],
)

recursive_cte_query = WithQueryExpression(
    dialect=dialect,
    ctes=[org_chart_cte],
    main_query=QueryExpression(
        dialect=dialect,
        select=[
            Column(dialect, 'id'),
            Column(dialect, 'name'),
            Column(dialect, 'department'),
            Column(dialect, 'level'),
        ],
        from_=TableExpression(dialect, 'org_chart'),
    ),
    recursive=True,
)

sql, params = recursive_cte_query.to_sql()
print(f"Recursive CTE SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expressions)
# ============================================================
options = ExecutionOptions(stmt_type=StatementType.DQL)

# Execute basic CTE
result = backend.execute(basic_cte_query.to_sql()[0], basic_cte_query.to_sql()[1], options=options)
print("\nBasic CTE - department headcounts:")
for row in result.data or []:
    print(f"  {row}")

# Execute recursive CTE
result = backend.execute(recursive_cte_query.to_sql()[0], recursive_cte_query.to_sql()[1], options=options)
print("\nRecursive CTE - org chart:")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
