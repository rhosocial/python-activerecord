from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from .....expression.objects import Table
from rhosocial.activerecord.backend.expression.advanced_functions import (  # noqa: E402
    WindowSpecification,
)
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression import (
    QueryStatement,
    Column,
    FunctionCall,
    OrderByClause,
)
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    CreateTableStatement,
    InsertStatement,
    ValuesSource,
)
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.expression.types import FloatType, IntegerType, TextType
"""
Window functions: ROW_NUMBER, LAG, LEAD.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect


create_table = CreateTableStatement(
    dialect=dialect,
    table_name="sales",
    columns=[
        ColumnDefinition(dialect, 
            "id",
            IntegerType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True)),
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, 
            "salesperson",
            TextType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, "region", TextType()),
        ColumnDefinition(dialect, "amount", FloatType()),
        ColumnDefinition(dialect, "sale_date", TextType()),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

sales_data = [
    ("Alice", "North", 1000, "2024-01-01"),
    ("Alice", "North", 1500, "2024-01-02"),
    ("Bob", "South", 1200, "2024-01-01"),
    ("Bob", "South", 1800, "2024-01-02"),
    ("Charlie", "North", 2000, "2024-01-01"),
]
for row in sales_data:
    insert_expr = InsertStatement(
        dialect=dialect,
        into=Table(dialect, 'sales'),
        columns=["salesperson", "region", "amount", "sale_date"],
        source=ValuesSource(dialect, [[Literal(dialect, v) for v in row]]),
    )
    sql, params = insert_expr.to_sql()
    backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

window_spec = WindowSpecification(
    dialect,
    partition_by=[Column(dialect, "salesperson")],
    order_by="sale_date",
)

window_func = FunctionCall(
    "ROW_NUMBER",
    window_spec=window_spec,
    alias="row_num",
)

query = QueryStatement(
    dialect=dialect,
    select=[
        Column(dialect, "salesperson"),
        Column(dialect, "amount"),
        Column(dialect, "sale_date"),
    ],
    from_=NamedRelationRef(dialect, Table(dialect, "sales")),
    order_by=OrderByClause(
        dialect,
        expressions=[(Column(dialect, "salesperson"), "ASC"), (Column(dialect, "sale_date"), "ASC")],
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
