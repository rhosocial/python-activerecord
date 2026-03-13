# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_generated_columns.py
"""Tests for SQLite generated columns support."""

import pytest
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    GeneratedColumnType,
    CreateTableExpression,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression import RawSQLExpression
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError


class TestGeneratedColumnsVersionSupport:
    """Test version detection for generated columns."""

    def test_supports_generated_columns_3_31_0(self):
        """Test that SQLite 3.31.0 supports generated columns."""
        dialect = SQLiteDialect(version=(3, 31, 0))
        assert dialect.supports_generated_columns() is True

    def test_supports_generated_columns_3_35_0(self):
        """Test that SQLite 3.35.0 supports generated columns."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        assert dialect.supports_generated_columns() is True

    def test_does_not_support_generated_columns_3_30_0(self):
        """Test that SQLite 3.30.0 does not support generated columns."""
        dialect = SQLiteDialect(version=(3, 30, 0))
        assert dialect.supports_generated_columns() is False

    def test_does_not_support_generated_columns_3_24_0(self):
        """Test that SQLite 3.24.0 does not support generated columns."""
        dialect = SQLiteDialect(version=(3, 24, 0))
        assert dialect.supports_generated_columns() is False


class TestGeneratedColumnsFormatting:
    """Test formatting of generated columns."""

    def test_virtual_generated_column(self):
        """Test formatting a VIRTUAL generated column."""
        dialect = SQLiteDialect(version=(3, 31, 0))
        
        col_def = ColumnDefinition(
            name="full_name",
            data_type="TEXT",
            generated_expression=RawSQLExpression(dialect, '"first_name" || \' \' || "last_name"'),
            generated_type=GeneratedColumnType.VIRTUAL
        )
        
        sql, params = dialect.format_column_definition(col_def)
        
        assert "GENERATED ALWAYS AS" in sql
        assert "VIRTUAL" in sql
        assert params == ()

    def test_stored_generated_column(self):
        """Test formatting a STORED generated column."""
        dialect = SQLiteDialect(version=(3, 31, 0))
        
        col_def = ColumnDefinition(
            name="total_price",
            data_type="REAL",
            generated_expression=RawSQLExpression(dialect, '"price" * "quantity"'),
            generated_type=GeneratedColumnType.STORED
        )
        
        sql, params = dialect.format_column_definition(col_def)
        
        assert "GENERATED ALWAYS AS" in sql
        assert "STORED" in sql
        assert params == ()

    def test_generated_column_default_virtual(self):
        """Test that generated column defaults to VIRTUAL when type not specified."""
        dialect = SQLiteDialect(version=(3, 31, 0))
        
        col_def = ColumnDefinition(
            name="computed_value",
            data_type="INTEGER",
            generated_expression=RawSQLExpression(dialect, '"base_value" + 1')
        )
        
        sql, params = dialect.format_column_definition(col_def)
        
        assert "GENERATED ALWAYS AS" in sql
        assert "VIRTUAL" in sql

    def test_generated_column_with_constraints(self):
        """Test generated column with additional constraints."""
        dialect = SQLiteDialect(version=(3, 31, 0))
        
        col_def = ColumnDefinition(
            name="status_code",
            data_type="INTEGER",
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)],
            generated_expression=RawSQLExpression(dialect, '"raw_status"')
        )
        
        sql, params = dialect.format_column_definition(col_def)
        
        assert "NOT NULL" in sql
        assert "GENERATED ALWAYS AS" in sql
        assert "VIRTUAL" in sql

    def test_generated_column_raises_error_on_unsupported_version(self):
        """Test that generated column raises error on unsupported version."""
        dialect = SQLiteDialect(version=(3, 30, 0))
        
        col_def = ColumnDefinition(
            name="computed",
            data_type="TEXT",
            generated_expression=RawSQLExpression(dialect, '"source"')
        )
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_column_definition(col_def)
        
        assert "Generated columns" in str(exc_info.value)
        assert "3.31.0" in str(exc_info.value)


class TestGeneratedColumnsInCreateTable:
    """Test generated columns in CREATE TABLE statements."""

    def test_create_table_with_generated_column(self):
        """Test CREATE TABLE with a generated column."""
        dialect = SQLiteDialect(version=(3, 31, 0))
        
        columns = [
            ColumnDefinition(
                name="id",
                data_type="INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
            ),
            ColumnDefinition(
                name="price",
                data_type="REAL"
            ),
            ColumnDefinition(
                name="quantity",
                data_type="INTEGER"
            ),
            ColumnDefinition(
                name="total",
                data_type="REAL",
                generated_expression=RawSQLExpression(dialect, '"price" * "quantity"'),
                generated_type=GeneratedColumnType.STORED
            )
        ]
        
        create_table = CreateTableExpression(
            dialect=dialect,
            table_name="order_items",
            columns=columns
        )
        
        sql, params = create_table.to_sql()
        
        assert 'CREATE TABLE "order_items"' in sql
        assert '"id" INTEGER PRIMARY KEY' in sql
        assert '"total" REAL GENERATED ALWAYS AS' in sql
        assert 'STORED' in sql

    def test_create_table_with_virtual_generated_column(self):
        """Test CREATE TABLE with a VIRTUAL generated column."""
        dialect = SQLiteDialect(version=(3, 31, 0))
        
        columns = [
            ColumnDefinition(
                name="id",
                data_type="INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
            ),
            ColumnDefinition(
                name="first_name",
                data_type="TEXT"
            ),
            ColumnDefinition(
                name="last_name",
                data_type="TEXT"
            ),
            ColumnDefinition(
                name="full_name",
                data_type="TEXT",
                generated_expression=RawSQLExpression(dialect, '"first_name" || \' \' || "last_name"'),
                generated_type=GeneratedColumnType.VIRTUAL
            )
        ]
        
        create_table = CreateTableExpression(
            dialect=dialect,
            table_name="users",
            columns=columns
        )
        
        sql, params = create_table.to_sql()
        
        assert 'CREATE TABLE "users"' in sql
        assert '"full_name" TEXT GENERATED ALWAYS AS' in sql
        assert 'VIRTUAL' in sql
