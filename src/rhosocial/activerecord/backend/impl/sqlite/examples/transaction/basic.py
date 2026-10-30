from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from .....expression.objects import Table
from rhosocial.activerecord.backend.expression.types import FloatType, IntegerType, TextType
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.core import Literal, Column
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression import (
    CreateTableStatement,
    InsertStatement,
    ValuesSource,
    UpdateStatement,
    QueryStatement,
    WhereClause,
)
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
"""
Basic transaction control using transaction manager.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect


create_table = CreateTableStatement(
    dialect=dialect,
    table_name="accounts",
    columns=[
        ColumnDefinition(dialect, 
            "id",
            IntegerType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, 
            "name",
            TextType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, "balance", FloatType()),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

insert = InsertStatement(
    dialect=dialect,
    into=Table(dialect, 'accounts'),
    columns=["name", "balance"],
    source=ValuesSource(
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
    update_expr = UpdateStatement(
        dialect=dialect,
        table=Table(dialect, 'accounts'),
        assignments={"balance": Literal(dialect, 50)},
        where=WhereClause(
            dialect,
            condition=ComparisonPredicate(
                "=",
                Column(dialect, "name"),
                Literal(dialect, "Alice"),
            ),
        ),
    )
    sql, params = update_expr.to_sql()
    backend.execute(sql, params)

# Verify
query = QueryStatement(
    dialect=dialect,
    select=[Column(dialect, "balance")],
    from_=NamedRelationRef(dialect, Table(dialect, "accounts")),
    where=WhereClause(
        dialect,
        condition=ComparisonPredicate(
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
