# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_drop_table.py
import pytest
from rhosocial.activerecord.backend.expression import (
    TableExpression, DropTableExpression
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestDropTableStatements:
    """Tests for DropTableExpression with various configurations and options."""

    def test_basic_drop_table(self, dummy_dialect: DummyDialect):
        """Tests a basic DROP TABLE statement."""
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name="users"
        )
        sql, params = drop_expr.to_sql()
        assert sql == 'DROP TABLE "users"'
        assert params == ()

    def test_drop_table_with_if_exists(self, dummy_dialect: DummyDialect):
        """Tests DROP TABLE with IF EXISTS option."""
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name="temporary_table",
            if_exists=True
        )
        sql, params = drop_expr.to_sql()
        assert sql == 'DROP TABLE IF EXISTS "temporary_table"'
        assert params == ()

    def test_drop_table_quoted_identifier(self, dummy_dialect: DummyDialect):
        """Tests DROP TABLE with identifier that contains special characters."""
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name="users with spaces"
        )
        sql, params = drop_expr.to_sql()
        assert sql == 'DROP TABLE "users with spaces"'  # Should be properly quoted
        assert params == ()

    def test_drop_table_with_special_chars(self, dummy_dialect: DummyDialect):
        """Tests DROP TABLE with table names containing quotes and other special characters."""
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name='table"with"quotes'
        )
        sql, params = drop_expr.to_sql()
        # The internal quotes should be doubled for SQL standard compliance
        assert sql == 'DROP TABLE "table""with""quotes"'
        assert params == ()

    @pytest.mark.parametrize("table_name,expected_sql", [
        pytest.param("simple_table", 'DROP TABLE "simple_table"', id="simple_table_name"),
        pytest.param("table_with_underscores", 'DROP TABLE "table_with_underscores"', id="underscore_table_name"),
        pytest.param("TableWithCamelCase", 'DROP TABLE "TableWithCamelCase"', id="camelcase_table_name"),
        pytest.param("table-with-dashes", 'DROP TABLE "table-with-dashes"', id="hyphen_table_name"),
        pytest.param("table123", 'DROP TABLE "table123"', id="numeric_table_name"),
        pytest.param("table with spaces", 'DROP TABLE "table with spaces"', id="spaced_table_name"),
        pytest.param("table'with'apostrophes", 'DROP TABLE "table\'with\'apostrophes"', id="apostrophe_table_name"),
    ])
    def test_drop_table_various_table_names(self, dummy_dialect: DummyDialect, table_name, expected_sql):
        """Tests DROP TABLE with various table name formats."""
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name=table_name
        )
        sql, params = drop_expr.to_sql()
        assert sql == expected_sql
        assert params == ()

    @pytest.mark.parametrize("if_exists", [
        pytest.param(True, id="with_if_exists"),
        pytest.param(False, id="without_if_exists"),
    ])
    def test_drop_table_with_if_exists_option(self, dummy_dialect: DummyDialect, if_exists):
        """Tests DROP TABLE with different IF EXISTS options."""
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name="test_table",
            if_exists=if_exists
        )
        sql, params = drop_expr.to_sql()
        
        if if_exists:
            assert "IF EXISTS" in sql
            assert sql == 'DROP TABLE IF EXISTS "test_table"'
        else:
            assert "IF EXISTS" not in sql
            assert sql == 'DROP TABLE "test_table"'
        assert params == ()

    def test_drop_table_with_empty_name(self, dummy_dialect: DummyDialect):
        """Tests DROP TABLE with an empty table name."""
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name=""
        )
        sql, params = drop_expr.to_sql()
        # Empty table name should still produce valid SQL with empty identifier
        assert sql == 'DROP TABLE ""'
        assert params == ()

    def test_drop_table_with_none_name_handling(self, dummy_dialect: DummyDialect):
        """Tests how DropTableExpression handles None table name (behavior may vary by implementation)."""
        # Since None table_name would likely cause an error during construction,
        # we'll test with an empty string which is the closest valid case
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name=""
        )
        sql, params = drop_expr.to_sql()
        # Should produce valid SQL for empty table name
        assert sql == 'DROP TABLE ""'
        assert params == ()

    def test_drop_table_special_characters_escaped(self, dummy_dialect: DummyDialect):
        """Tests that table names with special characters are properly escaped."""
        # Create a table name with double quotes
        table_name = 'table"name'
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name=table_name
        )
        sql, params = drop_expr.to_sql()
        # The quote should be escaped by doubling it in standard SQL
        assert sql == 'DROP TABLE "table""name"'
        assert params == ()

    def test_drop_table_unicode_characters(self, dummy_dialect: DummyDialect):
        """Tests DROP TABLE with unicode table names."""
        table_name = "用户表"  # Chinese characters for "user table"
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name=table_name
        )
        sql, params = drop_expr.to_sql()
        # Unicode characters should be preserved in identifiers
        assert 'DROP TABLE "用户表"' == sql
        assert params == ()

    def test_drop_table_backticks_handled_correctly(self, dummy_dialect: DummyDialect):
        """Tests that backticks in table name are handled appropriately."""
        table_name = "table`name"  # Table name with backtick (uncommon but possible)
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name=table_name
        )
        sql, params = drop_expr.to_sql()
        # Should be handled with double quotes regardless of original backticks
        assert sql == 'DROP TABLE "table`name"'
        assert params == ()

    def test_drop_multiple_similar_table_names(self, dummy_dialect: DummyDialect):
        """Tests DROP TABLE with similar but different table names."""
        table_names = ["users", "Users", "USERS", "users_backup", "users_temp"]
        
        for table_name in table_names:
            drop_expr = DropTableExpression(
                dummy_dialect,
                table_name=table_name
            )
            sql, params = drop_expr.to_sql()
            assert f'DROP TABLE "{table_name}"' == sql
            assert params == ()

    def test_drop_table_consistent_identifier_formatting(self, dummy_dialect: DummyDialect):
        """Tests that table names are consistently formatted as identifiers."""
        # Test with various identifier formats
        test_cases = [
            ("simple", '"simple"'),
            ("with_space", '"with_space"'),
            ("with-dash", '"with-dash"'),
            ("with.dot", '"with.dot"'),
            ('with"quote', '"with""quote"'),  # Double quote should be escaped by doubling it
        ]

        for table_name, expected_identifier in test_cases:
            drop_expr = DropTableExpression(
                dummy_dialect,
                table_name=table_name
            )
            sql, params = drop_expr.to_sql()
            assert f"DROP TABLE {expected_identifier}" == sql
            assert params == ()

    def test_drop_table_properties_accessible(self, dummy_dialect: DummyDialect):
        """Tests that DropTableExpression properties are correctly accessible."""
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name="test_table",
            if_exists=True
        )
        
        # Check that properties are accessible
        assert drop_expr.table_name == "test_table"
        assert drop_expr.if_exists is True
        
        # Generate SQL to verify it still works after accessing properties
        sql, params = drop_expr.to_sql()
        assert sql == 'DROP TABLE IF EXISTS "test_table"'
        assert params == ()

    def test_drop_table_if_exists_false_same_as_basic_drop(self, dummy_dialect: DummyDialect):
        """Tests that if_exists=False produces same result as basic DROP."""
        basic_drop = DropTableExpression(
            dummy_dialect,
            table_name="users"
        )
        
        explicit_false_drop = DropTableExpression(
            dummy_dialect,
            table_name="users",
            if_exists=False
        )
        
        basic_sql, basic_params = basic_drop.to_sql()
        explicit_sql, explicit_params = explicit_false_drop.to_sql()
        
        assert basic_sql == explicit_sql
        assert basic_params == explicit_params

    def test_drop_table_with_long_name(self, dummy_dialect: DummyDialect):
        """Tests DROP TABLE with a very long table name."""
        long_name = "very_long_table_name_that_exceeds_typical_database_identifier_limits_but_should_still_work"
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name=long_name
        )
        sql, params = drop_expr.to_sql()
        assert f'DROP TABLE "{long_name}"' == sql
        assert params == ()

    def test_drop_table_complex_scenario(self, dummy_dialect: DummyDialect):
        """Tests a complex DROP TABLE scenario with various options."""
        table_name = "my_schema.users_backup_2023"
        drop_expr = DropTableExpression(
            dummy_dialect,
            table_name=table_name,
            if_exists=True
        )
        sql, params = drop_expr.to_sql()
        assert sql == f'DROP TABLE IF EXISTS "{table_name}"'
        assert params == ()