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
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='orders',
    columns=[
        ColumnDefinition('id', 'INTEGER', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('user_id', 'INTEGER'),
        ColumnDefinition('amount', 'REAL'),
        ColumnDefinition('status', 'TEXT'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

orders_data = [
    (1, 100.0, 'completed'),
    (1, 200.0, 'completed'),
    (2, 150.0, 'completed'),
    (2, 50.0, 'pending'),
    (3, 300.0, 'completed'),
]
for row in orders_data:
    insert_expr = InsertExpression(
        dialect=dialect,
        into='orders',
        columns=['user_id', 'amount', 'status'],
        source=ValuesSource(dialect, [[Literal(dialect, v) for v in row]]),
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
