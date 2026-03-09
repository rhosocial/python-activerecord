# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_table_name_type_validation.py
"""Tests for table_name type validation in CreateTableExpression and DropTableExpression."""
import pytest
from rhosocial.activerecord.backend.expression import (
    TableExpression,
    CreateTableExpression,
    DropTableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestCreateTableExpressionTypeValidation:
    """Tests for CreateTableExpression table_name type validation."""

    def test_create_table_with_string_table_name(self, dummy_dialect: DummyDialect):
        """Tests CreateTableExpression accepts string table_name."""
        columns = [
            ColumnDefinition(
                name="id",
                data_type="INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
            ),
        ]
        
        expr = CreateTableExpression(dummy_dialect, "users", columns)
        assert isinstance(expr.table, TableExpression)
        assert expr.table.name == "users"
        assert expr.table.schema_name is None
        
        # Test backward compatibility property
        assert expr.table_name == "users"

    def test_create_table_with_table_expression(self, dummy_dialect: DummyDialect):
        """Tests CreateTableExpression accepts TableExpression object."""
        columns = [
            ColumnDefinition(
                name="id",
                data_type="INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
            ),
        ]
        
        table = TableExpression(dummy_dialect, "users")
        expr = CreateTableExpression(dummy_dialect, table, columns)
        assert expr.table is table
        assert expr.table.name == "users"

    def test_create_table_with_schema_qualified_table_expression(self, dummy_dialect: DummyDialect):
        """Tests CreateTableExpression accepts TableExpression with schema_name."""
        columns = [
            ColumnDefinition(
                name="id",
                data_type="INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
            ),
        ]
        
        table = TableExpression(dummy_dialect, "users", schema_name="public")
        expr = CreateTableExpression(dummy_dialect, table, columns)
        assert expr.table is table
        assert expr.table.name == "users"
        assert expr.table.schema_name == "public"
        
        sql, params = expr.to_sql()
        assert '"public"."users"' in sql

    def test_create_table_with_invalid_type_raises_error(self, dummy_dialect: DummyDialect):
        """Tests CreateTableExpression raises TypeError for invalid table_name type."""
        columns = [
            ColumnDefinition(
                name="id",
                data_type="INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
            ),
        ]
        
        # Test with integer
        with pytest.raises(TypeError) as exc_info:
            CreateTableExpression(dummy_dialect, 123, columns)
        assert "table_name must be str or TableExpression, got int" in str(exc_info.value)

    def test_create_table_with_none_raises_error(self, dummy_dialect: DummyDialect):
        """Tests CreateTableExpression raises TypeError for None table_name."""
        columns = [
            ColumnDefinition(
                name="id",
                data_type="INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
            ),
        ]
        
        with pytest.raises(TypeError) as exc_info:
            CreateTableExpression(dummy_dialect, None, columns)
        assert "table_name must be str or TableExpression, got NoneType" in str(exc_info.value)

    def test_create_table_with_list_raises_error(self, dummy_dialect: DummyDialect):
        """Tests CreateTableExpression raises TypeError for list table_name."""
        columns = [
            ColumnDefinition(
                name="id",
                data_type="INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
            ),
        ]
        
        with pytest.raises(TypeError) as exc_info:
            CreateTableExpression(dummy_dialect, ["users"], columns)
        assert "table_name must be str or TableExpression, got list" in str(exc_info.value)

    def test_create_table_with_dict_raises_error(self, dummy_dialect: DummyDialect):
        """Tests CreateTableExpression raises TypeError for dict table_name."""
        columns = [
            ColumnDefinition(
                name="id",
                data_type="INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
            ),
        ]
        
        with pytest.raises(TypeError) as exc_info:
            CreateTableExpression(dummy_dialect, {"name": "users"}, columns)
        assert "table_name must be str or TableExpression, got dict" in str(exc_info.value)


class TestDropTableExpressionTypeValidation:
    """Tests for DropTableExpression table_name type validation."""

    def test_drop_table_with_string_table_name(self, dummy_dialect: DummyDialect):
        """Tests DropTableExpression accepts string table_name."""
        expr = DropTableExpression(dummy_dialect, "users")
        assert isinstance(expr.table, TableExpression)
        assert expr.table.name == "users"
        assert expr.table.schema_name is None
        
        sql, params = expr.to_sql()
        assert sql == 'DROP TABLE "users"'
        assert params == ()

    def test_drop_table_with_table_expression(self, dummy_dialect: DummyDialect):
        """Tests DropTableExpression accepts TableExpression object."""
        table = TableExpression(dummy_dialect, "users")
        expr = DropTableExpression(dummy_dialect, table)
        assert expr.table is table
        assert expr.table.name == "users"

    def test_drop_table_with_schema_qualified_table_expression(self, dummy_dialect: DummyDialect):
        """Tests DropTableExpression accepts TableExpression with schema_name."""
        table = TableExpression(dummy_dialect, "users", schema_name="public")
        expr = DropTableExpression(dummy_dialect, table, if_exists=True, cascade=True)
        assert expr.table is table
        assert expr.table.name == "users"
        assert expr.table.schema_name == "public"
        
        sql, params = expr.to_sql()
        assert sql == 'DROP TABLE IF EXISTS "public"."users" CASCADE'
        assert params == ()

    def test_drop_table_with_invalid_type_raises_error(self, dummy_dialect: DummyDialect):
        """Tests DropTableExpression raises TypeError for invalid table_name type."""
        # Test with integer
        with pytest.raises(TypeError) as exc_info:
            DropTableExpression(dummy_dialect, 123)
        assert "table_name must be str or TableExpression, got int" in str(exc_info.value)

    def test_drop_table_with_none_raises_error(self, dummy_dialect: DummyDialect):
        """Tests DropTableExpression raises TypeError for None table_name."""
        with pytest.raises(TypeError) as exc_info:
            DropTableExpression(dummy_dialect, None)
        assert "table_name must be str or TableExpression, got NoneType" in str(exc_info.value)

    def test_drop_table_with_list_raises_error(self, dummy_dialect: DummyDialect):
        """Tests DropTableExpression raises TypeError for list table_name."""
        with pytest.raises(TypeError) as exc_info:
            DropTableExpression(dummy_dialect, ["users"])
        assert "table_name must be str or TableExpression, got list" in str(exc_info.value)

    def test_drop_table_with_dict_raises_error(self, dummy_dialect: DummyDialect):
        """Tests DropTableExpression raises TypeError for dict table_name."""
        with pytest.raises(TypeError) as exc_info:
            DropTableExpression(dummy_dialect, {"name": "users"})
        assert "table_name must be str or TableExpression, got dict" in str(exc_info.value)

    def test_drop_table_with_alias_in_table_expression(self, dummy_dialect: DummyDialect):
        """Tests DropTableExpression works with TableExpression having alias."""
        table = TableExpression(dummy_dialect, "users", alias="u")
        expr = DropTableExpression(dummy_dialect, table)
        assert expr.table.name == "users"
        assert expr.table.alias == "u"
        
        # Note: DROP TABLE includes alias if TableExpression has one
        sql, params = expr.to_sql()
        assert sql == 'DROP TABLE "users" AS "u"'
        assert params == ()
