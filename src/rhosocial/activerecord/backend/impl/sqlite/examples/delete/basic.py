"""
Delete records and return affected row count.
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
)
from rhosocial.activerecord.backend.expression.core import Literal  # noqa: E402
from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name="users",
    columns=[
        ColumnDefinition(
            "id",
            IntegerType(),
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
            ],
        ),
        ColumnDefinition(
            "name",
            TextType(),
            constraints=[
                ColumnConstraint(ColumnConstraintType.NOT_NULL),
            ],
        ),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert_expr = InsertExpression(
    dialect=dialect,
    into="users",
    columns=["name"],
    source=ValuesSource(dialect, [[Literal(dialect, "Alice")]]),
)
sql, params = insert_expr.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    DeleteExpression,
    ReturningClause,
    TableExpression,
    Column,
)
from rhosocial.activerecord.backend.expression.core import Literal  # noqa: E402
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate  # noqa: E402
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType

delete_expr = DeleteExpression(
    dialect=dialect,
    tables=TableExpression(dialect, "users"),
    where=ComparisonPredicate(
        dialect,
        "=",
        Column(dialect, "name"),
        Literal(dialect, "Alice"),
    ),
    returning=ReturningClause(dialect, [Column(dialect, "id")]),
    dialect_options={},
)

sql, params = delete_expr.to_sql()
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
