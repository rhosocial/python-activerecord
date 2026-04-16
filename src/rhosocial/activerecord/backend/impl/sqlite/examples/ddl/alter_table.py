"""
Alter table: add column, rename column, drop column.

Note: SQLite does not support multiple actions in a single ALTER TABLE statement.
Each action must be executed separately.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='users',
    columns=[
        ColumnDefinition('id', 'INTEGER', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('name', 'TEXT', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

insert_expr = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['name'],
    source=ValuesSource(dialect, [[Literal(dialect, 'Alice')]]),
)
sql, params = insert_expr.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    AlterTableExpression,
    ColumnDefinition,
)
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AddColumn,
    RenameColumn,
)

# Add a new column (separate statement for SQLite)
add_col_action = AddColumn(
    column=ColumnDefinition(
        name='email',
        data_type='TEXT',
    ),
)

add_col_expr = AlterTableExpression(
    dialect=dialect,
    table_name='users',
    actions=[add_col_action],
)

sql, params = add_col_expr.to_sql()
print(f"SQL (Add Column): {sql}")
print(f"Params: {params}")
backend.execute(sql, params)
print("Column added successfully")

# Rename a column (separate statement for SQLite)
rename_action = RenameColumn(
    old_name='name',
    new_name='full_name',
)

rename_expr = AlterTableExpression(
    dialect=dialect,
    table_name='users',
    actions=[rename_action],
)

sql, params = rename_expr.to_sql()
print(f"SQL (Rename Column): {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
backend.execute(sql, params)
print("Column renamed successfully")

# Verify using introspector
columns = backend.introspector.list_columns('users')
print("Table structure:")
for col in columns:
    print(f"  {col.name} {col.data_type}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
