# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_alter_table.py
import pytest

from rhosocial.activerecord.backend.expression import (
    Column, Literal, FunctionCall,
    ComparisonPredicate,  # Import ALTER TABLE related classes
    AlterTableExpression, AddColumn, DropColumn,
    ColumnDefinition, IndexDefinition
)
from rhosocial.activerecord.backend.expression.statements import (
    AlterColumn, AddConstraint, DropConstraint, RenameObject, AddIndex, DropIndex,
    TableConstraint, TableConstraintType, AddTableConstraint,
    DropTableConstraint, RenameColumn, RenameTable, ColumnAlterOperation
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

    def test_add_column_action_direct(self, dummy_dialect: DummyDialect):
        """Tests direct ADD COLUMN action creation and formatting."""
        column_def = ColumnDefinition(
            "phone",
            "VARCHAR(20)",
            comment="User's phone number"
        )
        add_action = AddColumn(column=column_def)
        # Since action doesn't have dialect yet, we need to create a full expression
        alter_expr = AlterTableExpression(dummy_dialect, "test_table", [add_action])
        # Get the action from the expression (which now has dialect injected)
        processed_action = alter_expr.actions[0]
        sql, params = processed_action.to_sql()

        assert "ADD COLUMN" in sql
        assert '"phone"' in sql
        assert "VARCHAR(20)" in sql
        assert params == ()

    def test_drop_column_action_direct(self, dummy_dialect: DummyDialect):
        """Tests direct DROP COLUMN action creation and formatting."""
        drop_action = DropColumn(column_name="old_phone")
        # Since action doesn't have dialect yet, we need to create a full expression
        alter_expr = AlterTableExpression(dummy_dialect, "test_table", [drop_action])
        # Get the action from the expression (which now has dialect injected)
        processed_action = alter_expr.actions[0]
        sql, params = processed_action.to_sql()

        assert "DROP COLUMN" in sql
        assert '"old_phone"' in sql
        assert params == ()

    def test_alter_column_action_direct(self, dummy_dialect: DummyDialect):
        """Tests direct ALTER COLUMN action creation and formatting."""
        alter_action = AlterColumn(
            column_name="description",
            operation="SET DEFAULT",
            new_value="default_value"
        )
        # Since action doesn't have dialect yet, we need to create a full expression
        alter_expr = AlterTableExpression(dummy_dialect, "test_table", [alter_action])
        # Get the action from the expression (which now has dialect injected)
        processed_action = alter_expr.actions[0]
        sql, params = processed_action.to_sql()

        assert "ALTER COLUMN" in sql
        assert '"description"' in sql
        assert "SET DEFAULT" in sql
        assert params == ("default_value",)

    def test_add_constraint_action_direct(self, dummy_dialect: DummyDialect):
        """Tests direct ADD CONSTRAINT action creation and formatting."""
        check_condition = Column(dummy_dialect, "balance") >= Literal(dummy_dialect, 0)
        constraint = TableConstraint(
            constraint_type=TableConstraintType.CHECK,
            check_condition=check_condition,
            name="chk_balance_positive"
        )
        add_constraint_action = AddConstraint(constraint=constraint)
        # Since action doesn't have dialect yet, we need to create a full expression
        alter_expr = AlterTableExpression(dummy_dialect, "test_table", [add_constraint_action])
        # Get the action from the expression (which now has dialect injected)
        processed_action = alter_expr.actions[0]
        sql, params = processed_action.to_sql()

        assert "ADD CONSTRAINT" in sql
        assert '"chk_balance_positive"' in sql
        assert params == (0,)  # From the literal value

    def test_drop_constraint_action_direct(self, dummy_dialect: DummyDialect):
        """Tests direct DROP CONSTRAINT action creation and formatting."""
        drop_constraint_action = DropConstraint(
            constraint_name="fk_old_constraint",
            cascade=True
        )
        # Since action doesn't have dialect yet, we need to create a full expression
        alter_expr = AlterTableExpression(dummy_dialect, "test_table", [drop_constraint_action])
        # Get the action from the expression (which now has dialect injected)
        processed_action = alter_expr.actions[0]
        sql, params = processed_action.to_sql()

        assert "DROP CONSTRAINT" in sql
        assert '"fk_old_constraint"' in sql
        assert "CASCADE" in sql
        assert params == ()

    def test_rename_column_action_direct(self, dummy_dialect: DummyDialect):
        """Tests direct RENAME COLUMN action creation and formatting."""
        rename_action = RenameObject(
            old_name="old_name",
            new_name="new_name",
            object_type="COLUMN"
        )
        # Since action doesn't have dialect yet, we need to create a full expression
        alter_expr = AlterTableExpression(dummy_dialect, "test_table", [rename_action])
        # Get the action from the expression (which now has dialect injected)
        processed_action = alter_expr.actions[0]
        sql, params = processed_action.to_sql()

        assert "RENAME COLUMN" in sql
        assert '"old_name"' in sql
        assert '"new_name"' in sql
        assert params == ()

    def test_add_index_action_direct(self, dummy_dialect: DummyDialect):
        """Tests direct ADD INDEX action creation and formatting."""
        index_def = IndexDefinition(
            name="idx_new_index",
            columns=["status"],
            unique=False
        )
        add_index_action = AddIndex(index=index_def)
        # Since action doesn't have dialect yet, we need to create a full expression
        alter_expr = AlterTableExpression(dummy_dialect, "test_table", [add_index_action])
        # Get the action from the expression (which now has dialect injected)
        processed_action = alter_expr.actions[0]
        sql, params = processed_action.to_sql()

        assert "ADD INDEX" in sql
        assert '"idx_new_index"' in sql
        assert params == ()

    def test_drop_index_action_direct(self, dummy_dialect: DummyDialect):
        """Tests direct DROP INDEX action creation and formatting."""
        drop_index_action = DropIndex(
            index_name="old_index",
            if_exists=True
        )
        # Since action doesn't have dialect yet, we need to create a full expression
        alter_expr = AlterTableExpression(dummy_dialect, "test_table", [drop_index_action])
        # Get the action from the expression (which now has dialect injected)
        processed_action = alter_expr.actions[0]
        sql, params = processed_action.to_sql()

        assert "DROP INDEX IF EXISTS" in sql
        assert '"old_index"' in sql
        assert params == ()

    def test_action_with_unknown_action_type(self, dummy_dialect: DummyDialect):
        """Tests handling of action with unknown action type."""
        # Create a custom action with an unknown action type
        class UnknownAction(AddColumn):
            def __init__(self, column):
                # Initialize with a column but set an unknown action type
                self.column = column
                self.action_type = "UNKNOWN_ACTION_TYPE"  # Use an unknown action type

        column_def = ColumnDefinition(
            "test_col",
            "VARCHAR(50)"
        )
        unknown_action = UnknownAction(column_def)
        # Manually inject dialect to test the else branch in to_sql
        unknown_action._dialect = dummy_dialect

        sql, params = unknown_action.to_sql()
        assert "PROCESS" in sql
        assert "UnknownAction" in sql  # Should contain the class name
        assert params == ()


    def test_action_without_dialect(self):
        """Tests handling of action without dialect set."""
        # Create an action without dialect
        add_action = AddColumn(column=ColumnDefinition("test", "VARCHAR(100)"))

        # Attempting to call to_sql should raise an error
        with pytest.raises(AttributeError, match="Dialect not set for AlterTableAction"):
            add_action.to_sql()

    def test_rename_column_action_standard(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with RENAME COLUMN action per SQL standard."""
        rename_action = RenameColumn(
            old_name="user_name",
            new_name="username"
        )

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="users",
            actions=[rename_action]
        )
        sql, params = alter_expr.to_sql()

        # Verify basic structure
        assert 'ALTER TABLE "users"' in sql
        assert 'RENAME COLUMN "user_name" TO "username"' in sql
        assert params == ()

    def test_rename_table_action_standard(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with RENAME TABLE action per SQL standard."""
        rename_action = RenameTable(
            old_name="old_table_name",
            new_name="new_table_name"
        )

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="old_table_name",
            actions=[rename_action]
        )
        sql, params = alter_expr.to_sql()

        # Verify basic structure
        assert 'ALTER TABLE "old_table_name"' in sql
        assert 'RENAME TO "new_table_name"' in sql
        assert params == ()

    def test_alter_column_set_default_standard(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with ALTER COLUMN SET DEFAULT action per SQL standard."""
        alter_action = AlterColumn(
            column_name="status",
            operation=ColumnAlterOperation.SET_DEFAULT,
            new_value="active"
        )

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="users",
            actions=[alter_action]
        )
        sql, params = alter_expr.to_sql()

        assert 'ALTER TABLE "users"' in sql
        assert 'ALTER COLUMN "status" SET DEFAULT' in sql
        assert params == ("active",)

    def test_alter_column_drop_default_standard(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with ALTER COLUMN DROP DEFAULT action per SQL standard."""
        alter_action = AlterColumn(
            column_name="status",
            operation=ColumnAlterOperation.DROP_DEFAULT
        )

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="users",
            actions=[alter_action]
        )
        sql, params = alter_expr.to_sql()

        assert 'ALTER TABLE "users"' in sql
        assert 'ALTER COLUMN "status" DROP DEFAULT' in sql
        assert params == ()

    def test_add_table_constraint_standard(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with ADD CONSTRAINT action per SQL standard."""
        check_condition = Column(dummy_dialect, "age") > Literal(dummy_dialect, 0)
        constraint = TableConstraint(
            constraint_type=TableConstraintType.CHECK,
            check_condition=check_condition,
            name="chk_positive_age"
        )
        add_constraint_action = AddTableConstraint(constraint=constraint)

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="employees",
            actions=[add_constraint_action]
        )
        sql, params = alter_expr.to_sql()

        # Verify basic structure
        assert 'ALTER TABLE "employees"' in sql
        assert 'ADD CONSTRAINT "chk_positive_age" CHECK' in sql
        assert params == (0,)

    def test_drop_table_constraint_standard(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with DROP CONSTRAINT action per SQL standard."""
        drop_constraint_action = DropTableConstraint(
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
        assert 'DROP CONSTRAINT "old_constraint"' in sql
        assert params == ()

    def test_drop_table_constraint_with_cascade_standard(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with DROP CONSTRAINT CASCADE per SQL standard."""
        drop_constraint_action = DropTableConstraint(
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
        assert 'DROP CONSTRAINT "fk_orders_user_id" CASCADE' in sql
        assert params == ()

    def test_drop_column_if_exists_standard(self, dummy_dialect: DummyDialect):
        """Tests ALTER TABLE with DROP COLUMN IF EXISTS per SQL standard."""
        drop_action = DropColumn(
            column_name="old_column",
            if_exists=True
        )

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="legacy_table",
            actions=[drop_action]
        )
        sql, params = alter_expr.to_sql()

        # Verify basic structure
        assert 'ALTER TABLE "legacy_table"' in sql
        assert 'DROP COLUMN IF EXISTS "old_column"' in sql
        assert params == ()

    def test_add_column_action_with_not_null_constraint(self, dummy_dialect: DummyDialect):
        """Tests ADD COLUMN with NOT NULL constraint (replacing the nullable=False functionality)."""
        from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint, ColumnConstraintType
        from rhosocial.activerecord.backend.expression.statements import AddColumn, AlterTableExpression

        column_def = ColumnDefinition(
            name="username",
            data_type="VARCHAR(50)",
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)],  # Use constraint instead of nullable flag
            comment="Username (cannot be null)"
        )
        add_action = AddColumn(column=column_def)

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="users",
            actions=[add_action]
        )
        sql, params = alter_expr.to_sql()

        # The exact format depends on the dialect's implementation of format_column_definition
        assert "ADD COLUMN" in sql
        assert '"username"' in sql
        assert "VARCHAR(50)" in sql
        # Check that NOT NULL was added due to the constraint
        assert "NOT NULL" in sql
        assert params == ()

    def test_add_column_action_with_null_constraint(self, dummy_dialect: DummyDialect):
        """Tests ADD COLUMN with explicit NULL constraint (replacing the nullable=True functionality)."""
        from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint, ColumnConstraintType
        from rhosocial.activerecord.backend.expression.statements import AddColumn, AlterTableExpression

        column_def = ColumnDefinition(
            name="description",
            data_type="TEXT",
            constraints=[ColumnConstraint(ColumnConstraintType.NULL)],  # Explicitly allow NULL
            comment="Description field"
        )
        add_action = AddColumn(column=column_def)

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="products",
            actions=[add_action]
        )
        sql, params = alter_expr.to_sql()

        # The exact format depends on the dialect's implementation of format_column_definition
        assert "ADD COLUMN" in sql
        assert '"description"' in sql
        assert "TEXT" in sql
        # Check that NULL was added due to the constraint
        assert " NULL" in sql  # Should have explicit NULL
        assert params == ()

    def test_add_column_action_with_default_constraint_literal(self, dummy_dialect: DummyDialect):
        """Tests ADD COLUMN with DEFAULT constraint using a literal value."""
        from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint, ColumnConstraintType
        from rhosocial.activerecord.backend.expression.statements import AddColumn, AlterTableExpression

        column_def = ColumnDefinition(
            name="status",
            data_type="VARCHAR(20)",
            constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="active")],  # Default value
            comment="Status field with default value"
        )
        add_action = AddColumn(column=column_def)

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="users",
            actions=[add_action]
        )
        sql, params = alter_expr.to_sql()

        # The exact format depends on the dialect's implementation of format_column_definition
        assert "ADD COLUMN" in sql
        assert '"status"' in sql
        assert "VARCHAR(20)" in sql
        # Check that DEFAULT was added due to the constraint
        assert "DEFAULT" in sql
        assert params == ("active",)  # Should have the default value as parameter

    def test_add_column_action_with_default_constraint_expression(self, dummy_dialect: DummyDialect):
        """Tests ADD COLUMN with DEFAULT constraint using an expression."""
        from rhosocial.activerecord.backend.expression import FunctionCall
        from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint, ColumnConstraintType
        from rhosocial.activerecord.backend.expression.statements import AddColumn, AlterTableExpression

        # Create a function call as default value
        now_func = FunctionCall(dummy_dialect, "NOW")

        column_def = ColumnDefinition(
            name="created_at",
            data_type="TIMESTAMP",
            constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=now_func)],  # Default function
            comment="Timestamp with default function"
        )
        add_action = AddColumn(column=column_def)

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="logs",
            actions=[add_action]
        )
        sql, params = alter_expr.to_sql()

        # The exact format depends on the dialect's implementation of format_column_definition
        assert "ADD COLUMN" in sql
        assert '"created_at"' in sql
        assert "TIMESTAMP" in sql
        # Check that DEFAULT was added with the function call
        assert "DEFAULT" in sql
        assert "NOW()" in sql
        assert params == ()  # Function calls don't have parameters

    def test_add_column_action_with_check_constraint(self, dummy_dialect: DummyDialect):
        """Tests ADD COLUMN with CHECK constraint."""
        from rhosocial.activerecord.backend.expression import Column as ExprColumn, Literal, ComparisonPredicate
        from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint, ColumnConstraintType
        from rhosocial.activerecord.backend.expression.statements import AddColumn, AlterTableExpression

        # Create a check condition: age > 0
        check_condition = ComparisonPredicate(
            dummy_dialect,
            ">",
            ExprColumn(dummy_dialect, "age"),
            Literal(dummy_dialect, 0)
        )

        column_def = ColumnDefinition(
            name="age",
            data_type="INTEGER",
            constraints=[ColumnConstraint(ColumnConstraintType.CHECK, check_condition=check_condition)],  # Check constraint
            comment="Age must be positive"
        )
        add_action = AddColumn(column=column_def)

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="people",
            actions=[add_action]
        )
        sql, params = alter_expr.to_sql()

        # The exact format depends on the dialect's implementation of format_column_definition
        assert "ADD COLUMN" in sql
        assert '"age"' in sql
        assert "INTEGER" in sql
        # Check that CHECK was added due to the constraint
        assert "CHECK" in sql
        assert params == (0,)  # Should have the check value as parameter

    def test_add_column_action_with_primary_key_constraint(self, dummy_dialect: DummyDialect):
        """Tests ADD COLUMN with PRIMARY KEY constraint."""
        from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint, ColumnConstraintType
        from rhosocial.activerecord.backend.expression.statements import AddColumn, AlterTableExpression

        column_def = ColumnDefinition(
            name="id",
            data_type="INTEGER",
            constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],  # Primary key constraint
            comment="Primary key column"
        )
        add_action = AddColumn(column=column_def)

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="new_table",
            actions=[add_action]
        )
        sql, params = alter_expr.to_sql()

        # The exact format depends on the dialect's implementation of format_column_definition
        assert "ADD COLUMN" in sql
        assert '"id"' in sql
        assert "INTEGER" in sql
        # Check that PRIMARY KEY was added due to the constraint
        assert "PRIMARY KEY" in sql
        assert params == ()

    def test_add_column_action_with_unique_constraint(self, dummy_dialect: DummyDialect):
        """Tests ADD COLUMN with UNIQUE constraint."""
        from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint, ColumnConstraintType
        from rhosocial.activerecord.backend.expression.statements import AddColumn, AlterTableExpression

        column_def = ColumnDefinition(
            name="email",
            data_type="VARCHAR(100)",
            constraints=[ColumnConstraint(ColumnConstraintType.UNIQUE)],  # Unique constraint
            comment="Unique email address"
        )
        add_action = AddColumn(column=column_def)

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="users",
            actions=[add_action]
        )
        sql, params = alter_expr.to_sql()

        # The exact format depends on the dialect's implementation of format_column_definition
        assert "ADD COLUMN" in sql
        assert '"email"' in sql
        assert "VARCHAR(100)" in sql
        # Check that UNIQUE was added due to the constraint
        assert "UNIQUE" in sql
        assert params == ()

    def test_add_column_action_with_foreign_key_constraint(self, dummy_dialect: DummyDialect):
        """Tests ADD COLUMN with FOREIGN KEY constraint."""
        from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint, ColumnConstraintType
        from rhosocial.activerecord.backend.expression.statements import AddColumn, AlterTableExpression

        column_def = ColumnDefinition(
            name="user_id",
            data_type="INTEGER",
            constraints=[ColumnConstraint(ColumnConstraintType.FOREIGN_KEY, foreign_key_reference=("users", ["id"]))],  # Foreign key constraint
            comment="Reference to users table"
        )
        add_action = AddColumn(column=column_def)

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="orders",
            actions=[add_action]
        )
        sql, params = alter_expr.to_sql()

        # The exact format depends on the dialect's implementation of format_column_definition
        assert "ADD COLUMN" in sql
        assert '"user_id"' in sql
        assert "INTEGER" in sql
        # Check that REFERENCES was added due to the foreign key constraint
        assert "REFERENCES" in sql
        assert '"users"' in sql
        assert '"id"' in sql
        assert params == ()

    def test_add_column_action_with_foreign_key_constraint_missing_reference(self, dummy_dialect: DummyDialect):
        """Tests ADD COLUMN with FOREIGN KEY constraint but missing foreign_key_reference should raise ValueError."""
        from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint, ColumnConstraintType
        from rhosocial.activerecord.backend.expression.statements import AddColumn, AlterTableExpression

        column_def = ColumnDefinition(
            name="user_id",
            data_type="INTEGER",
            constraints=[ColumnConstraint(ColumnConstraintType.FOREIGN_KEY)],  # Foreign key constraint without reference
            comment="Reference to users table"
        )
        add_action = AddColumn(column=column_def)

        alter_expr = AlterTableExpression(
            dummy_dialect,
            table_name="orders",
            actions=[add_action]
        )

        # Should raise ValueError when to_sql() is called
        with pytest.raises(ValueError, match=r"Foreign key constraint must have a foreign_key_reference specified."):
            alter_expr.to_sql()