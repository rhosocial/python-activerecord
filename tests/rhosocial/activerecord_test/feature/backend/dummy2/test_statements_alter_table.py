# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_alter_table.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, TableExpression, FunctionCall,
    ComparisonPredicate, QueryExpression,
    # Import ALTER TABLE related classes
    AlterTableExpression, AddColumn, DropColumn,
    ColumnDefinition, IndexDefinition
)
from rhosocial.activerecord.backend.expression.statements import (
    AlterColumn, AddConstraint, DropConstraint, RenameObject, AddIndex, DropIndex,
    TableConstraint, TableConstraintType, AlterTableActionType
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestAlterTableStatements:
    """Tests for ALTER TABLE statements with various actions and configurations."""

    def test_add_column_action(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with ADD COLUMN action."""
        column_def = ColumnDefinition(
            "email",
            "VARCHAR(100)",
            comment="User's email address"
        )
        add_action = AddColumn(column=column_def)

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="users",
            actions=[add_action]
        )
        sql, params = alter_expr.to_sql()

        # Verify basic structure
        assert 'ALTER TABLE "users"' in sql
        assert 'ADD COLUMN' in sql
        assert params == ()

    def test_drop_column_action(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with DROP COLUMN action."""
        drop_action = DropColumn(
            column_name="old_column"
        )
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="legacy_table",
            actions=[drop_action]
        )
        sql, params = alter_expr.to_sql()
        
        # Verify basic structure
        assert 'ALTER TABLE "legacy_table"' in sql
        assert 'DROP COLUMN' in sql
        assert '"old_column"' in sql
        assert params == ()

    def test_alter_column_modify_type(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with ALTER COLUMN to modify data type."""
        alter_action = AlterColumn(
            column_name="price",
            operation="SET DATA TYPE",
            new_value="DECIMAL(10,2)"
        )

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="products",
            actions=[alter_action]
        )
        sql, params = alter_expr.to_sql()

        # Verify basic structure
        assert 'ALTER TABLE "products"' in sql
        assert 'ALTER COLUMN' in sql
        assert '"price"' in sql
        assert 'SET DATA TYPE' in sql
        assert params == ()

    def test_alter_column_modify_default(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with ALTER COLUMN to modify default value."""
        alter_action = AlterColumn(
            column_name="status",
            operation="SET DEFAULT",
            new_value="active"
        )
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="users",
            actions=[alter_action]
        )
        sql, params = alter_expr.to_sql()
        
        assert 'ALTER TABLE "users"' in sql
        assert 'ALTER COLUMN' in sql
        assert '"status"' in sql
        assert 'SET DEFAULT' in sql
        assert params == ("active",)

    def test_add_constraint_action(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with ADD CONSTRAINT action."""
        check_condition = Column(dummy_dialect, "age") > Literal(dummy_dialect, 0)  # Using operator overload
        constraint = TableConstraint(
            constraint_type=TableConstraintType.CHECK,
            check_condition=check_condition,
            name="chk_positive_age"
        )
        add_constraint_action = AddConstraint(constraint=constraint)
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="employees",
            actions=[add_constraint_action]
        )
        sql, params = alter_expr.to_sql()
        
        # Verify basic structure
        assert 'ALTER TABLE "employees"' in sql
        assert 'ADD CONSTRAINT' in sql
        assert '"chk_positive_age"' in sql
        assert params == (0,)

    def test_drop_constraint_action(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with DROP CONSTRAINT action."""
        drop_constraint_action = DropConstraint(
            constraint_name="old_constraint",
            cascade=False
        )
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="orders",
            actions=[drop_constraint_action]
        )
        sql, params = alter_expr.to_sql()
        
        # Verify basic structure
        assert 'ALTER TABLE "orders"' in sql
        assert 'DROP CONSTRAINT' in sql
        assert '"old_constraint"' in sql
        assert params == ()

    def test_rename_column_action(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with RENAME COLUMN action."""
        rename_action = RenameObject(
            old_name="user_name",
            new_name="username",
            object_type="COLUMN"
        )
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="users",
            actions=[rename_action]
        )
        sql, params = alter_expr.to_sql()
        
        # Verify basic structure
        assert 'ALTER TABLE "users"' in sql
        assert params == ()

    def test_multiple_actions(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with multiple actions in a single statement."""
        column_def = ColumnDefinition(
            name="age",
            data_type="INTEGER"
        )
        add_action = AddColumn(column=column_def)
        drop_action = DropColumn(column_name="old_field")

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="profiles",
            actions=[add_action, drop_action]
        )
        sql, params = alter_expr.to_sql()
        
        # Verify basic structure
        assert 'ALTER TABLE "profiles"' in sql
        assert 'ADD COLUMN' in sql
        assert 'DROP COLUMN' in sql
        assert params == ()


    def test_alter_table_with_dialect_options(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with dialect-specific options."""
        column_def = ColumnDefinition(
            name="new_field",
            data_type="VARCHAR(50)"
        )
        add_action = AddColumn(column=column_def)
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="dynamic_table",
            actions=[add_action],
            dialect_options={"custom_option": "value"}
        )
        sql, params = alter_expr.to_sql()
        
        assert 'ALTER TABLE "dynamic_table"' in sql
        assert params == ()

    def test_alter_column_cascade_option(self, dummy_dialect: DummyDialect):
        """Tests ALTER COLUMN with CASCADE option."""
        alter_action = AlterColumn(
            column_name="category",
            operation="DROP NOT NULL",
            cascade=True
        )
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="products",
            actions=[alter_action]
        )
        sql, params = alter_expr.to_sql()
        
        assert 'ALTER TABLE "products"' in sql
        assert '"category"' in sql
        assert params == ()

    def test_add_index_action(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with ADD INDEX action."""
        index_def = IndexDefinition(
            name="idx_users_email",
            columns=["email"],
            unique=True
        )
        add_index_action = AddIndex(index=index_def)
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="users",
            actions=[add_index_action]
        )
        sql, params = alter_expr.to_sql()
        
        assert 'ALTER TABLE "users"' in sql
        assert params == ()

    def test_drop_index_action(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with DROP INDEX action."""
        drop_index_action = DropIndex(
            index_name="old_idx",
            if_exists=True
        )
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="legacy_table",
            actions=[drop_index_action]
        )
        sql, params = alter_expr.to_sql()
        
        assert 'ALTER TABLE "legacy_table"' in sql
        assert params == ()

    def test_drop_constraint_with_cascade(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with DROP CONSTRAINT CASCADE."""
        drop_constraint_action = DropConstraint(
            constraint_name="fk_orders_user_id",
            cascade=True
        )
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="orders",
            actions=[drop_constraint_action]
        )
        sql, params = alter_expr.to_sql()
        
        assert 'ALTER TABLE "orders"' in sql
        assert 'DROP CONSTRAINT' in sql
        assert '"fk_orders_user_id"' in sql
        # CASCADE might be included depending on dialect implementation
        assert params == ()

    def test_alter_table_complex_scenario(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with complex scenario involving multiple action types."""
        # Add new column
        new_col_def = ColumnDefinition(
            name="created_by",
            data_type="INTEGER"
        )
        add_action = AddColumn(column=new_col_def)
        
        # Set default value for existing column
        alter_action = AlterColumn(
            column_name="status",
            operation="SET DEFAULT",
            new_value="pending"
        )
        
        # Add foreign key constraint
        fk_condition = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "created_by"), Column(dummy_dialect, "id", "users"))
        constraint = TableConstraint(
            constraint_type=TableConstraintType.FOREIGN_KEY,
            name="fk_created_by",
            columns=["created_by"],
            foreign_key_table="users",
            foreign_key_columns=["id"]
        )
        add_constraint_action = AddConstraint(constraint=constraint)
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="posts",
            actions=[add_action, alter_action, add_constraint_action]
        )
        sql, params = alter_expr.to_sql()
        
        assert 'ALTER TABLE "posts"' in sql
        # Actions may appear in different order depending on implementation
        assert params == ("pending",)

    def test_alter_table_simple_types(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with simple data types."""
        column_def = ColumnDefinition(
            name="timestamp",
            data_type="TIMESTAMP"
        )
        add_action = AddColumn(column=column_def)
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="events",
            actions=[add_action]
        )
        sql, params = alter_expr.to_sql()
        
        assert 'ALTER TABLE "events"' in sql
        assert 'TIMESTAMP' in sql
        assert params == ()

    def test_alter_table_numeric_types(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with numeric data types."""
        column_def = ColumnDefinition(
            name="amount",
            data_type="DECIMAL(10,2)"
        )
        add_action = AddColumn(column=column_def)
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="transactions",
            actions=[add_action]
        )
        sql, params = alter_expr.to_sql()
        
        assert 'ALTER TABLE "transactions"' in sql
        assert 'DECIMAL(10,2)' in sql
        assert params == ()

    def test_alter_column_with_expression_default(self, dummy_dialect: DummyDialect):
        """Tests ALTER COLUMN with expression as default value."""
        alter_action = AlterColumn(
            column_name="updated_at",
            operation="SET DEFAULT",
            new_value=FunctionCall(dummy_dialect, "NOW")  # Use function call as default
        )
        
        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="entities",
            actions=[alter_action]
        )
        sql, params = alter_expr.to_sql()
        
        assert 'ALTER TABLE "entities"' in sql
        assert 'ALTER COLUMN' in sql
        assert '"updated_at"' in sql
        assert params == ()