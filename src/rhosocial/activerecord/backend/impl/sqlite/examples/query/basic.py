from rhosocial.activerecord.base.derivation import integer_auto_increment_parts  # noqa: E402
from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from .....expression.objects import Table
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.core import Parameter
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression import (
    QueryStatement,
    Column,
    WhereClause,
    OrderByClause,
    LimitOffsetClause,
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
Basic SELECT query with WHERE, ORDER BY, and LIMIT clauses.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect


create_table = CreateTableStatement(
    dialect=dialect,
    table_name="users",
    columns=[
        ColumnDefinition(dialect, 
            "id"[0],
            integer_auto_increment_parts(dialect, IntegerType())[0],
            constraints=[
                ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect)),
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
         attributes=integer_auto_increment_parts(dialect, IntegerType())[1]),
        ColumnDefinition(dialect, 
            "name",
            TextType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, "age", IntegerType()),
        ColumnDefinition(dialect, "status", TextType()),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

users = [
    ("Alice", 30, "active"),
    ("Bob", 25, "active"),
    ("Charlie", 35, "inactive"),
]
for row in users:
    insert_expr = InsertStatement(
        dialect=dialect,
        into=Table(dialect, 'users'),
        columns=["name", "age", "status"],
        source=ValuesSource(dialect, [[Parameter(dialect, v) for v in row]]),
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
        Column(dialect, "name"),
        Column(dialect, "age"),
    ],
    from_=NamedRelationRef(dialect, Table(dialect, "users")),
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(
            "=",
            Column(dialect, "status"),
            Parameter(dialect, "active"),
        ),
    ),
    order_by=OrderByClause(
        dialect,
        expressions=[(Column(dialect, "age"), "ASC")],
    ),
    limit_offset=LimitOffsetClause(dialect, limit=10),
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
