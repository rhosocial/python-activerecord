from rhosocial.activerecord.base.derivation import integer_auto_increment_parts  # noqa: E402
from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from .....expression.objects import Table
from rhosocial.activerecord.backend.expression.value_types.parameter import Parameter
from rhosocial.activerecord.backend.expression import (
    InsertStatement,
    ValuesSource,
    ReturningClause,
    Column,
)
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint
from rhosocial.activerecord.backend.expression import CreateTableStatement
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
"""
Insert a record and return the auto-generated ID using RETURNING clause.
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
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

insert_expr = InsertStatement(
    dialect=dialect,
    into=Table(dialect, 'users'),
    source=ValuesSource(dialect, [[Parameter(dialect, "Alice")]]),
    columns=["name"],
    returning=ReturningClause(dialect, [Column(dialect, "id")]),
)

sql, params = insert_expr.to_sql()
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
