"""
Window functions: ROW_NUMBER, LAG, LEAD.
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
    table_name='sales',
    columns=[
        ColumnDefinition('id', 'INTEGER', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('salesperson', 'TEXT', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
        ColumnDefinition('region', 'TEXT'),
        ColumnDefinition('amount', 'REAL'),
        ColumnDefinition('sale_date', 'TEXT'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

sales_data = [
    ('Alice', 'North', 1000, '2024-01-01'),
    ('Alice', 'North', 1500, '2024-01-02'),
    ('Bob', 'South', 1200, '2024-01-01'),
    ('Bob', 'South', 1800, '2024-01-02'),
    ('Charlie', 'North', 2000, '2024-01-01'),
]
for row in sales_data:
    insert_expr = InsertExpression(
        dialect=dialect,
        into='sales',
        columns=['salesperson', 'region', 'amount', 'sale_date'],
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
    OrderByClause,
)
from rhosocial.activerecord.backend.expression.advanced_functions import (
    WindowFunctionCall,
    WindowSpecification,
)

window_spec = WindowSpecification(
    dialect,
    partition_by=[Column(dialect, 'salesperson')],
    order_by='sale_date',
)

window_func = WindowFunctionCall(
    dialect,
    function_name='ROW_NUMBER',
    window_spec=window_spec,
    alias='row_num',
)

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'salesperson'),
        Column(dialect, 'amount'),
        Column(dialect, 'sale_date'),
        window_func,
    ],
    from_=TableExpression(dialect, 'sales'),
    order_by=OrderByClause(
        dialect,
        expressions=[(Column(dialect, 'salesperson'), 'ASC'), (Column(dialect, 'sale_date'), 'ASC')],
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
