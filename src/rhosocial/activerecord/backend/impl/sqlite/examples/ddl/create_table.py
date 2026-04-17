"""
Create a table with primary key, auto-increment, and index.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    IndexDefinition,
)

columns = [
    ColumnDefinition(
        name='id',
        data_type='INTEGER',
        constraints=[
            ColumnConstraint(
                constraint_type=ColumnConstraintType.PRIMARY_KEY,
                is_auto_increment=True,
            ),
        ],
    ),
    ColumnDefinition(
        name='name',
        data_type='TEXT',
        constraints=[
            ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL),
        ],
    ),
    ColumnDefinition(
        name='email',
        data_type='TEXT',
        constraints=[
            ColumnConstraint(constraint_type=ColumnConstraintType.UNIQUE),
        ],
    ),
    ColumnDefinition(
        name='created_at',
        data_type='TIMESTAMP',
    ),
]

indexes = [
    IndexDefinition(
        name='idx_users_email',
        columns=['email'],
    ),
]

create_expr = CreateTableExpression(
    dialect=dialect,
    table_name='users',
    columns=columns,
    indexes=indexes,
    if_not_exists=True,
    dialect_options={},
)

sql, params = create_expr.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(sql, params)
print("Table created: users")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()