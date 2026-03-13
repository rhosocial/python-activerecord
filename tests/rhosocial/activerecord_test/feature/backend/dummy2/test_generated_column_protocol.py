# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_generated_columns.py
import pytest
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition, ColumnConstraint, ColumnConstraintType,
    GeneratedColumnType, CreateTableExpression
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.dialect.protocols import GeneratedColumnSupport
from rhosocial.activerecord.backend.dialect.mixins import GeneratedColumnMixin


class TestGeneratedColumnProtocol:
    """Tests for GeneratedColumnSupport protocol."""

    def test_dummy_dialect_implements_protocol(self, dummy_dialect: DummyDialect):
        """Test that DummyDialect implements GeneratedColumnSupport protocol."""
        assert isinstance(dummy_dialect, GeneratedColumnSupport)

    def test_dummy_dialect_supports_generated_columns(self, dummy_dialect: DummyDialect):
        """Test that DummyDialect supports generated columns."""
        assert dummy_dialect.supports_generated_columns() is True
        assert dummy_dialect.supports_stored_generated_columns() is True
        assert dummy_dialect.supports_virtual_generated_columns() is True

    def test_mixin_default_values(self):
        """Test that GeneratedColumnMixin returns False by default."""
        class TestDialect(GeneratedColumnMixin):
            pass

        dialect = TestDialect()
        assert dialect.supports_generated_columns() is False
        assert dialect.supports_stored_generated_columns() is False
        assert dialect.supports_virtual_generated_columns() is False


class TestGeneratedColumnBasic:
    """Tests for basic generated column functionality."""

    def test_virtual_generated_column(self, dummy_dialect: DummyDialect):
        """Test CREATE TABLE with VIRTUAL generated column."""
        columns = [
            ColumnDefinition("id", "INTEGER",
                             constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("first_name", "VARCHAR(50)",
                             constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("last_name", "VARCHAR(50)",
                             constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("full_name", "VARCHAR(101)",
                             generated_expression=(Column(dummy_dialect, "first_name") + 
                                                   Literal(dummy_dialect, " ") + 
                                                   Column(dummy_dialect, "last_name")),
                             generated_type=GeneratedColumnType.VIRTUAL)
        ]

        create_table = CreateTableExpression(
            dummy_dialect,
            table_name="users",
            columns=columns
        )
        sql, params = create_table.to_sql()

        assert 'CREATE TABLE "users"' in sql
        assert '"full_name" VARCHAR(101) GENERATED ALWAYS AS' in sql
        assert 'VIRTUAL' in sql
        # Literal values generate parameters
        assert len(params) == 1
        assert params[0] == ' '

    def test_stored_generated_column(self, dummy_dialect: DummyDialect):
        """Test CREATE TABLE with STORED generated column."""
        columns = [
            ColumnDefinition("id", "INTEGER",
                             constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("price", "DECIMAL(10,2)"),
            ColumnDefinition("quantity", "INTEGER"),
            ColumnDefinition("total", "DECIMAL(10,2)",
                             generated_expression=(Column(dummy_dialect, "price") * 
                                                   Column(dummy_dialect, "quantity")),
                             generated_type=GeneratedColumnType.STORED)
        ]

        create_table = CreateTableExpression(
            dummy_dialect,
            table_name="order_items",
            columns=columns
        )
        sql, params = create_table.to_sql()

        assert 'CREATE TABLE "order_items"' in sql
        assert '"total" DECIMAL(10,2) GENERATED ALWAYS AS' in sql
        assert 'STORED' in sql
        assert params == ()

    def test_generated_column_default_virtual(self, dummy_dialect: DummyDialect):
        """Test that generated column defaults to VIRTUAL when type not specified."""
        columns = [
            ColumnDefinition("id", "INTEGER",
                             constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("computed", "INTEGER",
                             generated_expression=(Column(dummy_dialect, "id") + 
                                                   Literal(dummy_dialect, 1)))
        ]

        create_table = CreateTableExpression(
            dummy_dialect,
            table_name="test_table",
            columns=columns
        )
        sql, params = create_table.to_sql()

        assert '"computed" INTEGER GENERATED ALWAYS AS' in sql
        assert 'VIRTUAL' in sql or 'STORED' in sql


class TestGeneratedColumnWithConstraints:
    """Tests for generated columns combined with other constraints."""

    def test_generated_column_with_not_null(self, dummy_dialect: DummyDialect):
        """Test generated column cannot have NOT NULL constraint."""
        columns = [
            ColumnDefinition("id", "INTEGER",
                             constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("value", "INTEGER",
                             constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)],
                             generated_expression=(Column(dummy_dialect, "id") * 
                                                   Literal(dummy_dialect, 2)),
                             generated_type=GeneratedColumnType.VIRTUAL)
        ]

        create_table = CreateTableExpression(
            dummy_dialect,
            table_name="test_table",
            columns=columns
        )
        sql, params = create_table.to_sql()

        assert '"value" INTEGER NOT NULL GENERATED ALWAYS AS' in sql


class TestGeneratedColumnExpressions:
    """Tests for various expression types in generated columns."""

    def test_arithmetic_expression(self, dummy_dialect: DummyDialect):
        """Test generated column with arithmetic expression."""
        columns = [
            ColumnDefinition("a", "INTEGER"),
            ColumnDefinition("b", "INTEGER"),
            ColumnDefinition("sum_result", "INTEGER",
                             generated_expression=(Column(dummy_dialect, "a") + 
                                                   Column(dummy_dialect, "b")),
                             generated_type=GeneratedColumnType.VIRTUAL)
        ]

        create_table = CreateTableExpression(
            dummy_dialect,
            table_name="math_table",
            columns=columns
        )
        sql, params = create_table.to_sql()

        assert '"sum_result" INTEGER GENERATED ALWAYS AS' in sql
        assert '+ "b"' in sql

    def test_string_concatenation(self, dummy_dialect: DummyDialect):
        """Test generated column with string concatenation."""
        columns = [
            ColumnDefinition("first", "VARCHAR(50)"),
            ColumnDefinition("last", "VARCHAR(50)"),
            ColumnDefinition("full", "VARCHAR(101)",
                             generated_expression=(Column(dummy_dialect, "first") + 
                                                   Literal(dummy_dialect, " ") + 
                                                   Column(dummy_dialect, "last")),
                             generated_type=GeneratedColumnType.STORED)
        ]

        create_table = CreateTableExpression(
            dummy_dialect,
            table_name="names",
            columns=columns
        )
        sql, params = create_table.to_sql()

        assert '"full" VARCHAR(101) GENERATED ALWAYS AS' in sql
        assert 'STORED' in sql
