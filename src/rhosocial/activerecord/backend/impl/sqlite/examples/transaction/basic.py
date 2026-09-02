"""
Basic transaction control using transaction manager.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import (  # noqa: E402
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
    UpdateExpression,
    QueryExpression,
    TableExpression,
    WhereClause,
)
from rhosocial.activerecord.backend.expression.core import Literal, Column  # noqa: E402
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate  # noqa: E402
from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.options import ExecutionOptions  # noqa: E402
from rhosocial.activerecord.backend.schema import StatementType  # noqa: E402
from rhosocial.activerecord.backend.expression.types import FloatType, IntegerType, TextType

create_table = CreateTableExpression(
    dialect=dialect,
    table="accounts",
    columns=[
        ColumnDefinition(
            "id",
            IntegerType(),
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ],
        ),
        ColumnDefinition(
            "name",
            TextType(),
            constraints=[
                ColumnConstraint(ColumnConstraintType.NOT_NULL),
            ],
        ),
        ColumnDefinition("balance", FloatType()),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    into="accounts",
    columns=["name", "balance"],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, "Alice"), Literal(dialect, 100)],
        ],
    ),
)
sql, params = insert.to_sql()
print(f"Insert SQL: {sql}")
backend.execute(sql, params)

dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
# The transaction is used as a context manager, no special import needed

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
with backend.transaction():
    update_expr = UpdateExpression(
        dialect=dialect,
        table="accounts",
        assignments={"balance": Literal(dialect, 50)},
        where=WhereClause(
            dialect,
            condition=ComparisonPredicate(
                dialect,
                "=",
                Column(dialect, "name"),
                Literal(dialect, "Alice"),
            ),
        ),
    )
    sql, params = update_expr.to_sql()
    backend.execute(sql, params)

# Verify
query = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, "balance")],
    from_=TableExpression(dialect, "accounts"),
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            "=",
            Column(dialect, "name"),
            Literal(dialect, "Alice"),
        ),
    ),
)
sql, params = query.to_sql()
result = backend.execute(sql, params, options=dql_options)
if result.data:
    print(f"Balance after transaction: {result.data[0]['balance']}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
