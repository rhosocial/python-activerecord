# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_dialect_column_constraints.py
"""
Tests for SQLiteDialect column constraint handling methods.

These tests validate the refactored constraint handler methods that use
a strategy pattern with dictionary dispatch to reduce cognitive complexity.
"""
import pytest
from unittest.mock import Mock, MagicMock
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    GeneratedColumnType,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError


class TestColumnConstraintHandlers:
    """Test individual constraint handler methods."""

    def test_handle_primary_key_constraint(self):
        """Test PRIMARY KEY constraint handler."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(constraint_type=ColumnConstraintType.PRIMARY_KEY)

        sql, params = dialect._handle_primary_key_constraint(constraint)

        assert sql == " PRIMARY KEY"
        assert params == ()

    def test_handle_not_null_constraint(self):
        """Test NOT NULL constraint handler."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL)

        sql, params = dialect._handle_not_null_constraint(constraint)

        assert sql == " NOT NULL"
        assert params == ()

    def test_handle_null_constraint(self):
        """Test NULL constraint handler."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(constraint_type=ColumnConstraintType.NULL)

        sql, params = dialect._handle_null_constraint(constraint)

        assert sql == " NULL"
        assert params == ()

    def test_handle_unique_constraint(self):
        """Test UNIQUE constraint handler."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(constraint_type=ColumnConstraintType.UNIQUE)

        sql, params = dialect._handle_unique_constraint(constraint)

        assert sql == " UNIQUE"
        assert params == ()

    def test_handle_default_constraint_with_simple_value(self):
        """Test DEFAULT constraint handler with simple value."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(
            constraint_type=ColumnConstraintType.DEFAULT,
            default_value="test_default"
        )

        sql, params = dialect._handle_default_constraint(constraint)

        assert sql == " DEFAULT ?"
        assert params == ("test_default",)

    def test_handle_default_constraint_with_expression(self):
        """Test DEFAULT constraint handler with expression value."""
        from rhosocial.activerecord.backend.expression import bases

        dialect = SQLiteDialect()
        # Use spec to make isinstance check work
        mock_expr = MagicMock(spec=bases.BaseExpression)
        mock_expr.to_sql.return_value = ("CURRENT_TIMESTAMP", ())
        constraint = ColumnConstraint(
            constraint_type=ColumnConstraintType.DEFAULT,
            default_value=mock_expr
        )

        sql, params = dialect._handle_default_constraint(constraint)

        assert sql == " DEFAULT CURRENT_TIMESTAMP"
        assert params == ()

    def test_handle_default_constraint_missing_value(self):
        """Test DEFAULT constraint handler raises error when value is missing."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(
            constraint_type=ColumnConstraintType.DEFAULT,
            default_value=None
        )

        with pytest.raises(ValueError, match="DEFAULT constraint must have a default value"):
            dialect._handle_default_constraint(constraint)

    def test_handle_check_constraint_with_condition(self):
        """Test CHECK constraint handler with condition."""
        dialect = SQLiteDialect()
        mock_condition = Mock()
        mock_condition.to_sql.return_value = ("age > 0", ())
        constraint = ColumnConstraint(
            constraint_type=ColumnConstraintType.CHECK,
            check_condition=mock_condition
        )

        sql, params = dialect._handle_check_constraint(constraint)

        assert sql == " CHECK (age > 0)"
        assert params == ()

    def test_handle_check_constraint_without_condition(self):
        """Test CHECK constraint handler without condition returns empty."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(
            constraint_type=ColumnConstraintType.CHECK,
            check_condition=None
        )

        sql, params = dialect._handle_check_constraint(constraint)

        assert sql == ""
        assert params == ()

    def test_handle_foreign_key_constraint(self):
        """Test FOREIGN KEY constraint handler."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(
            constraint_type=ColumnConstraintType.FOREIGN_KEY,
            foreign_key_reference=("users", ["id"])
        )

        sql, params = dialect._handle_foreign_key_constraint(constraint)

        assert sql == ' REFERENCES "users"("id")'
        assert params == ()

    def test_handle_foreign_key_constraint_multiple_columns(self):
        """Test FOREIGN KEY constraint with multiple columns."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(
            constraint_type=ColumnConstraintType.FOREIGN_KEY,
            foreign_key_reference=("orders", ["user_id", "order_id"])
        )

        sql, params = dialect._handle_foreign_key_constraint(constraint)

        assert sql == ' REFERENCES "orders"("user_id", "order_id")'
        assert params == ()

    def test_handle_foreign_key_constraint_missing_reference(self):
        """Test FOREIGN KEY constraint handler raises error when reference is missing."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(
            constraint_type=ColumnConstraintType.FOREIGN_KEY,
            foreign_key_reference=None
        )

        with pytest.raises(ValueError, match="Foreign key constraint must have a foreign_key_reference"):
            dialect._handle_foreign_key_constraint(constraint)


class TestGeneratedColumnHandler:
    """Test generated column handler method."""

    def test_handle_generated_column_virtual(self):
        """Test generated column handler with VIRTUAL type."""
        dialect = SQLiteDialect((3, 31, 0))  # Version supporting generated columns
        mock_expr = Mock()
        mock_expr.to_sql.return_value = ("first_name || ' ' || last_name", ())

        col_def = Mock()
        col_def.generated_expression = mock_expr
        col_def.generated_type = GeneratedColumnType.VIRTUAL

        sql, params = dialect._handle_generated_column(col_def)

        assert sql == " GENERATED ALWAYS AS (first_name || ' ' || last_name) VIRTUAL"
        assert params == ()

    def test_handle_generated_column_stored(self):
        """Test generated column handler with STORED type."""
        dialect = SQLiteDialect((3, 31, 0))
        mock_expr = Mock()
        mock_expr.to_sql.return_value = ("price * quantity", ())

        col_def = Mock()
        col_def.generated_expression = mock_expr
        col_def.generated_type = GeneratedColumnType.STORED

        sql, params = dialect._handle_generated_column(col_def)

        assert sql == " GENERATED ALWAYS AS (price * quantity) STORED"
        assert params == ()

    def test_handle_generated_column_unsupported_version(self):
        """Test generated column handler raises error for unsupported SQLite version."""
        dialect = SQLiteDialect((3, 30, 0))  # Version NOT supporting generated columns
        mock_expr = Mock()
        col_def = Mock()
        col_def.generated_expression = mock_expr

        with pytest.raises(UnsupportedFeatureError, match="Generated columns require SQLite 3.31.0"):
            dialect._handle_generated_column(col_def)


class TestFormatColumnDefinition:
    """Test the refactored format_column_definition method."""

    def test_format_column_definition_basic(self):
        """Test basic column definition without constraints."""
        dialect = SQLiteDialect()
        col_def = ColumnDefinition(
            name="id",
            data_type="INTEGER"
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"id" INTEGER'
        assert params == ()

    def test_format_column_definition_with_primary_key(self):
        """Test column definition with PRIMARY KEY constraint."""
        dialect = SQLiteDialect()
        col_def = ColumnDefinition(
            name="id",
            data_type="INTEGER",
            constraints=[ColumnConstraint(constraint_type=ColumnConstraintType.PRIMARY_KEY)]
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"id" INTEGER PRIMARY KEY'
        assert params == ()

    def test_format_column_definition_with_multiple_constraints(self):
        """Test column definition with multiple constraints."""
        dialect = SQLiteDialect()
        col_def = ColumnDefinition(
            name="email",
            data_type="VARCHAR(255)",
            constraints=[
                ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL),
                ColumnConstraint(constraint_type=ColumnConstraintType.UNIQUE),
            ]
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"email" VARCHAR(255) NOT NULL UNIQUE'
        assert params == ()

    def test_format_column_definition_with_default(self):
        """Test column definition with DEFAULT constraint."""
        dialect = SQLiteDialect()
        col_def = ColumnDefinition(
            name="status",
            data_type="VARCHAR(50)",
            constraints=[
                ColumnConstraint(
                    constraint_type=ColumnConstraintType.DEFAULT,
                    default_value="active"
                )
            ]
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"status" VARCHAR(50) DEFAULT ?'
        assert params == ("active",)

    def test_format_column_definition_with_check(self):
        """Test column definition with CHECK constraint."""
        dialect = SQLiteDialect()
        mock_condition = Mock()
        mock_condition.to_sql.return_value = ("age >= 18", ())

        col_def = ColumnDefinition(
            name="age",
            data_type="INTEGER",
            constraints=[
                ColumnConstraint(
                    constraint_type=ColumnConstraintType.CHECK,
                    check_condition=mock_condition
                )
            ]
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"age" INTEGER CHECK (age >= 18)'
        assert params == ()

    def test_format_column_definition_with_foreign_key(self):
        """Test column definition with FOREIGN KEY constraint."""
        dialect = SQLiteDialect()
        col_def = ColumnDefinition(
            name="user_id",
            data_type="INTEGER",
            constraints=[
                ColumnConstraint(
                    constraint_type=ColumnConstraintType.FOREIGN_KEY,
                    foreign_key_reference=("users", ["id"])
                )
            ]
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"user_id" INTEGER REFERENCES "users"("id")'
        assert params == ()

    def test_format_column_definition_with_generated_column(self):
        """Test column definition with generated column."""
        dialect = SQLiteDialect((3, 31, 0))
        mock_expr = Mock()
        mock_expr.to_sql.return_value = ("first_name || ' ' || last_name", ())

        col_def = ColumnDefinition(
            name="full_name",
            data_type="VARCHAR(255)",
            generated_expression=mock_expr,
            generated_type=GeneratedColumnType.VIRTUAL
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"full_name" VARCHAR(255) GENERATED ALWAYS AS (first_name || \' \' || last_name) VIRTUAL'
        assert params == ()

    def test_format_column_definition_with_all_constraint_types(self):
        """Test column definition with all constraint types in sequence."""
        dialect = SQLiteDialect()
        mock_condition = Mock()
        mock_condition.to_sql.return_value = ("value > 0", ())

        col_def = ColumnDefinition(
            name="price",
            data_type="DECIMAL(10,2)",
            constraints=[
                ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL),
                ColumnConstraint(constraint_type=ColumnConstraintType.DEFAULT, default_value=0.0),
                ColumnConstraint(constraint_type=ColumnConstraintType.CHECK, check_condition=mock_condition),
            ]
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"price" DECIMAL(10,2) NOT NULL DEFAULT ? CHECK (value > 0)'
        assert params == (0.0,)

    def test_format_column_definition_null_constraint(self):
        """Test column definition with NULL constraint."""
        dialect = SQLiteDialect()
        col_def = ColumnDefinition(
            name="optional_field",
            data_type="VARCHAR(100)",
            constraints=[ColumnConstraint(constraint_type=ColumnConstraintType.NULL)]
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"optional_field" VARCHAR(100) NULL'
        assert params == ()
