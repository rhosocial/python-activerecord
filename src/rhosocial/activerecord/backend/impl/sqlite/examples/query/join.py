from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
    TableForeignKeyConstraint,
)
from .....expression.objects import Table
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression import (
    QueryStatement,
    Column,
    JoinClause,
)
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint, TableConstraint
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
"""
JOIN query with multiple tables.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect


users_table = CreateTableStatement(
    dialect=dialect,
    table_name="users",
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
            "name",
            TextType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
        ),
    ],
    if_not_exists=True,
)
sql, params = users_table.to_sql()
backend.execute(sql, params)

orders_table = CreateTableStatement(
    dialect=dialect,
    table_name="orders",
    columns=[
        ColumnDefinition(dialect, 
            "id",
            IntegerType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True)),
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, "user_id", IntegerType()),
        ColumnDefinition(dialect, "amount", FloatType()),
    ],
    table_constraints=[
        TableConstraint(dialect, branch=TableForeignKeyConstraint(dialect, ["user_id"], "users", ["id"])),
    ],
    if_not_exists=True,
)
sql, params = orders_table.to_sql()
backend.execute(sql, params)

users = [("Alice",), ("Bob",)]
for user in users:
    insert_expr = InsertStatement(
        dialect=dialect,
        into=Table(dialect, 'users'),
        columns=["name"],
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
    insert_expr = InsertStatement(
        dialect=dialect,
        into=Table(dialect, 'orders'),
        columns=["user_id", "amount"],
        source=ValuesSource(dialect, [[Literal(dialect, v) for v in row]]),
    )
    sql, params = insert_expr.to_sql()
    backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

join_expr = JoinClause(
    dialect=dialect,
    left_table=NamedRelationRef(dialect, Table(dialect, "users"), alias="u"),
    right_table=NamedRelationRef(dialect, Table(dialect, "orders"), alias="o"),
    join_type="LEFT JOIN",
    condition=ComparisonPredicate(
        "=",
        Column(dialect, "id", "u"),
        Column(dialect, "user_id", "o"),
    ),
)

query = QueryStatement(
    dialect=dialect,
    select=[
        Column(dialect, "name", "u"),
        Column(dialect, "amount", "o"),
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
