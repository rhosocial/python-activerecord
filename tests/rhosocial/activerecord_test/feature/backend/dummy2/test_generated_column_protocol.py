# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_generated_columns.py
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    GeneratedColumnType,
    GeneratedColumnExpression,
    CreateTableExpression,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.dialect.protocols import GeneratedColumnSupport
from rhosocial.activerecord.backend.dialect.mixins import GeneratedColumnMixin
from rhosocial.activerecord.backend.expression.types import DecimalType, IntegerType, VarCharType


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


class TestGeneratedColumnExpression:
    """Tests for GeneratedColumnExpression as standalone expression."""

    def test_to_sql_stored(self, dummy_dialect: DummyDialect):
        """Test GeneratedColumnExpression.to_sql() for STORED."""
        gen = GeneratedColumnExpression(
            dummy_dialect,
            expression=Column(dummy_dialect, "price") * Column(dummy_dialect, "qty"),
            storage_type=GeneratedColumnType.STORED,
        )
        sql, params = gen.to_sql()
        assert "GENERATED ALWAYS AS" in sql
        assert "STORED" in sql
        assert '"price"' in sql
        assert params == ()

    def test_to_sql_virtual(self, dummy_dialect: DummyDialect):
        """Test GeneratedColumnExpression.to_sql() for VIRTUAL."""
        gen = GeneratedColumnExpression(
            dummy_dialect,
            expression=Column(dummy_dialect, "a") + Column(dummy_dialect, "b"),
        )
        sql, params = gen.to_sql()
        assert "GENERATED ALWAYS AS" in sql
        assert "VIRTUAL" in sql
        assert params == ()

    def test_default_storage_is_virtual(self, dummy_dialect: DummyDialect):
        """Test that default storage type is VIRTUAL."""
        gen = GeneratedColumnExpression(
            dummy_dialect,
            expression=Column(dummy_dialect, "x"),
        )
        assert gen.storage_type == GeneratedColumnType.VIRTUAL


class TestGeneratedColumnBasic:
    """Tests for basic generated column functionality."""

    def test_virtual_generated_column(self, dummy_dialect: DummyDialect):
        """Test CREATE TABLE with VIRTUAL generated column."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dummy_dialect,
                "first_name", VarCharType(dummy_dialect, 50), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.NOT_NULL)]
            ),
            ColumnDefinition(dummy_dialect, "last_name", VarCharType(dummy_dialect, 50), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dummy_dialect,
                "full_name",
                VarCharType(dummy_dialect, 101),
                generated_expression=GeneratedColumnExpression(
                    dummy_dialect,
                    expression=(
                        Column(dummy_dialect, "first_name")
                        + Literal(dummy_dialect, " ", inline_literals=True)
                        + Column(dummy_dialect, "last_name")
                    ),
                    storage_type=GeneratedColumnType.VIRTUAL,
                ),
            ),
        ]

        create_table = CreateTableExpression(dummy_dialect, table="users", columns=columns)
        sql, params = create_table.to_sql()

        assert 'CREATE TABLE "users"' in sql
        assert '"full_name" VARCHAR(101) GENERATED ALWAYS AS' in sql
        assert "VIRTUAL" in sql
        assert params == ()

    def test_stored_generated_column(self, dummy_dialect: DummyDialect):
        """Test CREATE TABLE with STORED generated column."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dummy_dialect, "price", DecimalType(dummy_dialect, precision=10, scale=2)),
            ColumnDefinition(dummy_dialect, "quantity", IntegerType(dummy_dialect)),
            ColumnDefinition(dummy_dialect,
                "total",
                DecimalType(dummy_dialect, precision=10, scale=2),
                generated_expression=GeneratedColumnExpression(
                    dummy_dialect,
                    expression=Column(dummy_dialect, "price") * Column(dummy_dialect, "quantity"),
                    storage_type=GeneratedColumnType.STORED,
                ),
            ),
        ]

        create_table = CreateTableExpression(dummy_dialect, table="order_items", columns=columns)
        sql, params = create_table.to_sql()

        assert 'CREATE TABLE "order_items"' in sql
        assert '"total" DECIMAL(10,2) GENERATED ALWAYS AS' in sql
        assert "STORED" in sql
        assert params == ()

    def test_generated_column_default_virtual(self, dummy_dialect: DummyDialect):
        """Test that generated column defaults to VIRTUAL when type not specified."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dummy_dialect,
                "computed", IntegerType(dummy_dialect),
                generated_expression=GeneratedColumnExpression(
                    dummy_dialect,
                    expression=Column(dummy_dialect, "id") + Literal(dummy_dialect, 1),
                ),
            ),
        ]

        create_table = CreateTableExpression(dummy_dialect, table="test_table", columns=columns)
        sql, params = create_table.to_sql()

        assert '"computed" INTEGER GENERATED ALWAYS AS' in sql
        assert "VIRTUAL" in sql


class TestGeneratedColumnWithConstraints:
    """Tests for generated columns combined with other constraints."""

    def test_generated_column_with_not_null(self, dummy_dialect: DummyDialect):
        """Test generated column with NOT NULL constraint."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dummy_dialect,
                "value",
                IntegerType(dummy_dialect),
                constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.NOT_NULL)],
                generated_expression=GeneratedColumnExpression(
                    dummy_dialect,
                    expression=Column(dummy_dialect, "id") * Literal(dummy_dialect, 2),
                    storage_type=GeneratedColumnType.VIRTUAL,
                ),
            ),
        ]

        create_table = CreateTableExpression(dummy_dialect, table="test_table", columns=columns)
        sql, params = create_table.to_sql()

        assert '"value" INTEGER NOT NULL GENERATED ALWAYS AS' in sql


class TestGeneratedColumnExpressions:
    """Tests for various expression types in generated columns."""

    def test_arithmetic_expression(self, dummy_dialect: DummyDialect):
        """Test generated column with arithmetic expression."""
        columns = [
            ColumnDefinition(dummy_dialect, "a", IntegerType(dummy_dialect)),
            ColumnDefinition(dummy_dialect, "b", IntegerType(dummy_dialect)),
            ColumnDefinition(dummy_dialect,
                "sum_result",
                IntegerType(dummy_dialect),
                generated_expression=GeneratedColumnExpression(
                    dummy_dialect,
                    expression=Column(dummy_dialect, "a") + Column(dummy_dialect, "b"),
                    storage_type=GeneratedColumnType.VIRTUAL,
                ),
            ),
        ]

        create_table = CreateTableExpression(dummy_dialect, table="math_table", columns=columns)
        sql, params = create_table.to_sql()

        assert '"sum_result" INTEGER GENERATED ALWAYS AS' in sql
        assert '+ "b"' in sql

    def test_string_concatenation(self, dummy_dialect: DummyDialect):
        """Test generated column with string concatenation."""
        columns = [
            ColumnDefinition(dummy_dialect, "first", VarCharType(dummy_dialect, 50)),
            ColumnDefinition(dummy_dialect, "last", VarCharType(dummy_dialect, 50)),
            ColumnDefinition(dummy_dialect,
                "full",
                VarCharType(dummy_dialect, 101),
                generated_expression=GeneratedColumnExpression(
                    dummy_dialect,
                    expression=Column(dummy_dialect, "first") + Literal(dummy_dialect, " ") + Column(dummy_dialect, "last"),
                    storage_type=GeneratedColumnType.STORED,
                ),
            ),
        ]

        create_table = CreateTableExpression(dummy_dialect, table="names", columns=columns)
        sql, params = create_table.to_sql()

        assert '"full" VARCHAR(101) GENERATED ALWAYS AS' in sql
        assert "STORED" in sql
