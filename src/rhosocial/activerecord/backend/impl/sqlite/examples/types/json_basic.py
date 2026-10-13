from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from .....expression.objects import Table
from rhosocial.activerecord.backend.expression.core import FunctionCall, Literal
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression import (
    QueryStatement,
    Column,
)
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    CreateTableStatement,
    InsertStatement,
    ValuesSource,
)
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
"""
JSON operations using JSON functions.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect


create_table = CreateTableStatement(
    dialect=dialect,
    table_name="documents",
    columns=[
        ColumnDefinition(dialect, 
            "id",
            IntegerType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True)),
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, "data", TextType()),
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
for data in insert_data:
    insert_expr = InsertStatement(
        dialect=dialect,
        into=Table(dialect, 'documents'),
        columns=["data"],
        source=ValuesSource(dialect, [[Literal(dialect, json.dumps(data))]]),
    )
    sql, params = insert_expr.to_sql()
    backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

query = QueryStatement(
    dialect=dialect,
    select=[
        Column(dialect, "id"),
        FunctionCall(dialect, "json_extract", Column(dialect, "data"), Literal(dialect, "$.name")),
    ],
    from_=NamedRelationRef(dialect, Table(dialect, "documents")),
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
