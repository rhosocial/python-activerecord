"""
JSON operations using JSON functions.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect


# Version-gated features (RETURNING, JSON1, math functions) read the
# dialect version, which is only known after the server is inspected.
backend.introspect_and_adapt()
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.core import Literal  # noqa: E402
from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

from rhosocial.activerecord.backend.expression.types import IntegerType, TextType
create_table = CreateTableExpression(
    dialect=dialect,
    table="documents",
    columns=[
        ColumnDefinition(dialect, 
            "id",
            IntegerType(dialect),
            constraints=[
                ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY),
                ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL, is_auto_increment=True),
            ],
        ),
        ColumnDefinition(dialect, "data", TextType(dialect)),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

import json  # noqa: E402

insert_data = [
    {"name": "Alice", "age": 30, "tags": ["a", "b"]},
    {"name": "Bob", "age": 25, "tags": ["c"]},
]
from rhosocial.activerecord.backend.expression.core import FunctionCall, Literal  # noqa: E402
for data in insert_data:
    insert_expr = InsertExpression(
        dialect=dialect,
        into="documents",
        columns=["data"],
        source=ValuesSource(dialect, [[Literal(dialect, json.dumps(data))]]),
    )
    sql, params = insert_expr.to_sql()
    backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    QueryExpression,
    TableExpression,
    Column,
)

query = QueryExpression(
    dialect=dialect,
    select=[
        Column(dialect, "id"),
        FunctionCall(dialect, "json_extract", Column(dialect, "data"), Literal(dialect, "$.name")),
    ],
    from_=TableExpression(dialect, "documents"),
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
