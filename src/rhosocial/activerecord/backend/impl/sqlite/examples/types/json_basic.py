"""
JSON operations using JSON functions.
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
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='documents',
    columns=[
        ColumnDefinition('id', 'INTEGER', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('data', 'TEXT'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

import json
insert_data = [
    {'name': 'Alice', 'age': 30, 'tags': ['a', 'b']},
    {'name': 'Bob', 'age': 25, 'tags': ['c']},
]
for data in insert_data:
    insert_expr = InsertExpression(
        dialect=dialect,
        into='documents',
        columns=['data'],
        source=ValuesSource(dialect, [[Literal(dialect, json.dumps(data))]]),
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
)
from rhosocial.activerecord.backend.expression.core import FunctionCall, Literal

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, 'id'),
        FunctionCall(dialect, 'json_extract', Column(dialect, 'data'), Literal(dialect, '$.name')),
    ],
    from_=TableExpression(dialect, 'documents'),
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
