from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from .....expression.objects import Table
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression import (
    UpdateStatement,
    ReturningClause,
    Column,
)
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    CreateTableStatement,
    InsertStatement,
    ValuesSource,
)
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
"""
Update records and return the updated IDs using RETURNING clause.
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
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert_expr = InsertStatement(
    dialect=dialect,
    into=Table(dialect, 'users'),
    columns=["name"],
    source=ValuesSource(dialect, [[Literal(dialect, "Alice")]]),
)
sql, params = insert_expr.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

update_expr = UpdateStatement(
    dialect=dialect,
    table=Table(dialect, 'users'),
    assignments={"name": Literal(dialect, "Alice Smith")},
    where=ComparisonPredicate(
        "=",
        Column(dialect, "name"),
        Literal(dialect, "Alice"),
    ),
    returning=ReturningClause(dialect, [Column(dialect, "id"), Column(dialect, "name")]),
)

sql, params = update_expr.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(sql, params)
print(f"Affected rows: {result.affected_rows}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
