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

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    TableConstraint,
    TableConstraintType,
)

users_table = CreateTableExpression(
    dialect=dialect,
    table_name='users',
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
sql, params = users_table.to_sql()
backend.execute(sql, params)

orders_table = CreateTableExpression(
    dialect=dialect,
    table_name='orders',
    columns=[
        ColumnDefinition('id', 'INTEGER', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('user_id', 'INTEGER'),
        ColumnDefinition('amount', 'REAL'),
    ],
    table_constraints=[
        TableConstraint(
            constraint_type=TableConstraintType.FOREIGN_KEY,
            columns=['user_id'],
            foreign_key_table='users',
            foreign_key_columns=['id'],
        ),
    ],
    if_not_exists=True,
)
sql, params = orders_table.to_sql()
backend.execute(sql, params)

users = [('Alice',), ('Bob',)]
for user in users:
    insert_expr = InsertExpression(
        dialect=dialect,
        into='users',
        columns=['name'],
        source=ValuesSource(dialect, [[Literal(dialect, v) for v in user]]),
    )
    sql, params = insert_expr.to_sql()
    backend.execute(sql, params)

orders = [
    (1, 100.0),
    (1, 200.0),
    (2, 150.0),
]
for row in orders:
    insert_expr = InsertExpression(
        dialect=dialect,
        into='orders',
        columns=['user_id', 'amount'],
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
