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
    ColumnGeneratedConstraint,
    GeneratedColumnType,
    ColumnCheckConstraint,
    ColumnDefaultConstraint,
    ColumnForeignKeyConstraint,
    ColumnNotNullConstraint,
    ColumnNullableConstraint,
    ColumnPrimaryKeyConstraint,
    ColumnUniqueConstraint,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
    SQLiteIntegerType,
    SQLiteNumericType,
    SQLiteTextType,
)
from rhosocial.activerecord.backend.expression.objects import Table


class TestColumnConstraintHandlers:
    """Test individual constraint handler methods."""

    def test_handle_primary_key_constraint(self):
        """Test PRIMARY KEY constraint handler."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))

        sql, params = dialect.format_column_primary_key_constraint(constraint.branch)

        assert sql == " PRIMARY KEY"
        assert params == ()

    def test_handle_not_null_constraint(self):
        """Test NOT NULL constraint handler."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))

        sql, params = dialect.format_column_constraint(constraint)

        assert sql == " NOT NULL"
        assert params == ()

    def test_handle_null_constraint(self):
        """Test NULL constraint handler."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(dialect, branch=ColumnNullableConstraint(dialect))

        sql, params = dialect.format_column_constraint(constraint)

        assert sql == " NULL"
        assert params == ()

    def test_handle_unique_constraint(self):
        """Test UNIQUE constraint handler."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect))

        sql, params = dialect.format_column_constraint(constraint)

        assert sql == " UNIQUE"
        assert params == ()

    def test_handle_default_constraint_with_simple_value(self):
        """Test DEFAULT constraint handler with simple value."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, "test_default"))

        sql, params = dialect.format_column_default_constraint(constraint.branch)

        assert sql == " DEFAULT 'test_default'"
        assert params == ()

    def test_handle_default_constraint_with_expression(self):
        """Test DEFAULT constraint handler with expression value."""
        from rhosocial.activerecord.backend.expression import bases, ColumnDefaultConstraint

        dialect = SQLiteDialect()
        # Use spec to make isinstance check work
        mock_expr = MagicMock(spec=bases.BaseExpression)
        mock_expr.to_sql.return_value = ("CURRENT_TIMESTAMP", ())
        constraint = ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, mock_expr))

        sql, params = dialect.format_column_default_constraint(constraint.branch)

        assert sql == " DEFAULT CURRENT_TIMESTAMP"
        assert params == ()

    def test_handle_default_constraint_missing_value(self):
        """Test DEFAULT constraint handler raises error when value is missing."""
        dialect = SQLiteDialect()
        with pytest.raises(ValueError, match="needs a value"):
            ColumnDefaultConstraint(dialect, None)

    def test_handle_check_constraint_with_condition(self):
        """Test CHECK constraint handler with condition."""
        dialect = SQLiteDialect()
        mock_condition = Mock()
        mock_condition.to_sql.return_value = ("age > 0", ())
        constraint = ColumnConstraint(dialect, branch=ColumnCheckConstraint(dialect, mock_condition))

        sql, params = dialect.format_column_constraint(constraint)

        assert sql == " CHECK (age > 0)"
        assert params == ()

    def test_handle_check_constraint_without_condition(self):
        """A predicate-less CHECK is reported, not silently dropped."""
        dialect = SQLiteDialect()
        with pytest.raises(ValueError, match="needs a condition"):
            ColumnCheckConstraint(dialect, None)

    def test_handle_foreign_key_constraint(self):
        """Test FOREIGN KEY constraint handler."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(dialect, branch=ColumnForeignKeyConstraint(dialect, (Table(dialect, "users"), ["id"])))

        sql, params = dialect.format_column_constraint(constraint)

        assert sql == ' REFERENCES "users"("id")'
        assert params == ()

    def test_handle_foreign_key_constraint_multiple_columns(self):
        """Test FOREIGN KEY constraint with multiple columns."""
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(dialect, branch=ColumnForeignKeyConstraint(dialect, (Table(dialect, "orders"), ["user_id", "order_id"])))

        sql, params = dialect.format_column_constraint(constraint)

        assert sql == ' REFERENCES "orders"("user_id", "order_id")'
        assert params == ()

    def test_handle_foreign_key_constraint_missing_reference(self):
        """Test FOREIGN KEY constraint handler raises error when reference is missing."""
        dialect = SQLiteDialect()
        with pytest.raises(ValueError, match="needs references"):
            ColumnForeignKeyConstraint(dialect, None)


class TestGeneratedColumnHandler:
    """Test generated column handler method."""

    def test_handle_generated_column_virtual(self):
        """Test generated column expression with VIRTUAL type."""
        dialect = SQLiteDialect((3, 31, 0))
        mock_expr = Mock()
        mock_expr.to_sql.return_value = ("first_name || ' ' || last_name", ())

        gen = ColumnGeneratedConstraint(
            dialect,
            expression=mock_expr,
            storage_type=GeneratedColumnType.VIRTUAL,
        )
        sql, params = gen.to_sql()

        assert sql == " GENERATED ALWAYS AS (first_name || ' ' || last_name) VIRTUAL"
        assert params == ()

    def test_handle_generated_column_stored(self):
        """Test generated column expression with STORED type."""
        dialect = SQLiteDialect((3, 31, 0))
        mock_expr = Mock()
        mock_expr.to_sql.return_value = ("price * quantity", ())

        gen = ColumnGeneratedConstraint(
            dialect,
            expression=mock_expr,
            storage_type=GeneratedColumnType.STORED,
        )
        sql, params = gen.to_sql()

        assert sql == " GENERATED ALWAYS AS (price * quantity) STORED"
        assert params == ()

    def test_handle_generated_column_unsupported_version(self):
        """Test generated column raises error for unsupported SQLite version."""
        dialect = SQLiteDialect((3, 30, 0))  # Version NOT supporting generated columns
        mock_expr = Mock()
        mock_expr.to_sql.return_value = ("col1 + 1", ())

        gen = ColumnGeneratedConstraint(
            dialect,
            expression=mock_expr,
            storage_type=GeneratedColumnType.VIRTUAL,
        )

        with pytest.raises(UnsupportedFeatureError, match="Generated columns"):
            gen.to_sql()


class TestFormatColumnDefinition:
    """Test the refactored format_column_definition method."""

    def test_format_column_definition_basic(self):
        """Test basic column definition without constraints."""
        dialect = SQLiteDialect()
        col_def = ColumnDefinition(dialect, name="id", data_type=SQLiteIntegerType(dialect))

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"id" INTEGER'
        assert params == ()

    def test_format_column_definition_with_primary_key(self):
        """Test column definition with PRIMARY KEY constraint."""
        dialect = SQLiteDialect()
        col_def = ColumnDefinition(dialect, 
            name="id",
            data_type=SQLiteIntegerType(dialect),
            constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))],
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"id" INTEGER PRIMARY KEY'
        assert params == ()

    def test_format_column_definition_with_multiple_constraints(self):
        """Test column definition with multiple constraints."""
        dialect = SQLiteDialect()
        col_def = ColumnDefinition(dialect, 
            name="email",
            data_type=SQLiteTextType(dialect, 255),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect)),
            ],
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"email" TEXT(255) NOT NULL UNIQUE'
        assert params == ()

    def test_format_column_definition_with_default(self):
        """Test column definition with DEFAULT constraint."""
        dialect = SQLiteDialect()
        col_def = ColumnDefinition(dialect, 
            name="status",
            data_type=SQLiteTextType(dialect, 50),
            constraints=[ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, "active"))],
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"status" TEXT(50) DEFAULT \'active\''
        assert params == ()

    def test_format_column_definition_with_check(self):
        """Test column definition with CHECK constraint."""
        dialect = SQLiteDialect()
        mock_condition = Mock()
        mock_condition.to_sql.return_value = ("age >= 18", ())

        col_def = ColumnDefinition(dialect, 
            name="age",
            data_type=SQLiteIntegerType(dialect),
            constraints=[ColumnConstraint(dialect, branch=ColumnCheckConstraint(dialect, mock_condition))],
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"age" INTEGER CHECK (age >= 18)'
        assert params == ()

    def test_format_column_definition_with_foreign_key(self):
        """Test column definition with FOREIGN KEY constraint."""
        dialect = SQLiteDialect()
        col_def = ColumnDefinition(dialect, 
            name="user_id",
            data_type=SQLiteIntegerType(dialect),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnForeignKeyConstraint(dialect, (Table(dialect, "users"), ["id"])))
            ],
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"user_id" INTEGER REFERENCES "users"("id")'
        assert params == ()

    def test_format_column_definition_with_generated_column(self):
        """Test column definition with generated column."""
        dialect = SQLiteDialect((3, 31, 0))
        mock_expr = Mock()
        mock_expr.to_sql.return_value = ("first_name || ' ' || last_name", ())

        col_def = ColumnDefinition(dialect,
            name="full_name",
            data_type=SQLiteTextType(dialect, 255),
            generated_expression=ColumnGeneratedConstraint(
                dialect,
                expression=mock_expr,
                storage_type=GeneratedColumnType.VIRTUAL,
            ),
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == "\"full_name\" TEXT(255) GENERATED ALWAYS AS (first_name || ' ' || last_name) VIRTUAL"
        assert params == ()

    def test_format_column_definition_with_all_constraint_types(self):
        """Test column definition with all constraint types in sequence."""
        dialect = SQLiteDialect()
        mock_condition = Mock()
        mock_condition.to_sql.return_value = ("value > 0", ())

        col_def = ColumnDefinition(dialect, 
            name="price",
            data_type=SQLiteNumericType(dialect, 10, 2),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, 0.0)),
                ColumnConstraint(dialect, branch=ColumnCheckConstraint(dialect, mock_condition)),
            ],
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"price" NUMERIC NOT NULL DEFAULT 0.0 CHECK (value > 0)'
        assert params == ()

    def test_format_column_definition_null_constraint(self):
        """Test column definition with NULL constraint."""
        dialect = SQLiteDialect()
        col_def = ColumnDefinition(dialect, 
            name="optional_field",
            data_type=SQLiteTextType(dialect, 100),
            constraints=[ColumnConstraint(dialect, branch=ColumnNullableConstraint(dialect))],
        )

        sql, params = dialect.format_column_definition(col_def)

        assert sql == '"optional_field" TEXT(100) NULL'
        assert params == ()
