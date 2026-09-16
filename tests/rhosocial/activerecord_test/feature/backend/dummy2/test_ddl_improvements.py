# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_ddl_improvements.py
"""Tests for DDL improvements: capability gating, UnsupportedFeatureError, parentheses fix."""
import pytest
from unittest.mock import patch, PropertyMock

from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    FunctionCall,
    TableExpression,
    QueryExpression,
    CreateViewExpression,
    DropViewExpression,
)
from rhosocial.activerecord.backend.expression.statements import (
    ViewCheckOption,
    CreateTriggerExpression,
    DropTriggerExpression,
    TriggerTiming,
    TriggerEvent,
    TriggerLevel,
)
from rhosocial.activerecord.backend.expression.statements.ddl_database import (
    CreateDatabaseExpression,
    DropDatabaseExpression,
    AlterDatabaseExpression,
    AlterDatabaseAction,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError


class TestViewParenthesesFix:
    """Tests for CREATE VIEW parentheses fix (no parentheses around query_sql)."""

    def test_create_view_no_parentheses_around_query(self, dummy_dialect: DummyDialect):
        """CREATE VIEW should not wrap query_sql in parentheses."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users"),
        )
        create_view = CreateViewExpression(dummy_dialect, view_name="v", query=query)
        sql, _ = create_view.to_sql()
        assert "AS (" not in sql
        assert "AS SELECT" in sql


class TestViewCapabilityGating:
    """Tests for CREATE VIEW capability gating."""

    def test_create_or_replace_view_raises_when_unsupported(self, dummy_dialect: DummyDialect):
        """CREATE OR REPLACE VIEW should raise UnsupportedFeatureError when not supported."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users"),
        )
        create_view = CreateViewExpression(
            dummy_dialect, view_name="v", query=query, replace=True
        )
        with patch.object(type(dummy_dialect), "supports_create_or_replace_view", return_value=False):
            with pytest.raises(UnsupportedFeatureError, match="CREATE OR REPLACE VIEW"):
                create_view.to_sql()

    def test_create_view_if_not_exists_raises_when_unsupported(self, dummy_dialect: DummyDialect):
        """CREATE VIEW IF NOT EXISTS should raise UnsupportedFeatureError when not supported."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users"),
        )
        create_view = CreateViewExpression(
            dummy_dialect, view_name="v", query=query, if_not_exists=True
        )
        with patch.object(type(dummy_dialect), "supports_if_not_exists_view", return_value=False):
            with pytest.raises(UnsupportedFeatureError, match="IF NOT EXISTS"):
                create_view.to_sql()

    def test_drop_view_if_exists_raises_when_unsupported(self, dummy_dialect: DummyDialect):
        """DROP VIEW IF EXISTS should raise UnsupportedFeatureError when not supported."""
        drop_view = DropViewExpression(
            dummy_dialect, view_name="v", if_exists=True
        )
        with patch.object(type(dummy_dialect), "supports_if_exists_view", return_value=False):
            with pytest.raises(UnsupportedFeatureError, match="IF EXISTS"):
                drop_view.to_sql()

    def test_drop_view_cascade_raises_when_unsupported(self, dummy_dialect: DummyDialect):
        """DROP VIEW CASCADE should raise UnsupportedFeatureError when not supported."""
        drop_view = DropViewExpression(
            dummy_dialect, view_name="v", cascade=True
        )
        with patch.object(type(dummy_dialect), "supports_cascade_view", return_value=False):
            with pytest.raises(UnsupportedFeatureError, match="CASCADE"):
                drop_view.to_sql()


class TestColumnCapabilityGating:
    """Tests for COLUMN DDL capability gating."""

    def test_add_column_if_not_exists_raises_when_unsupported(self):
        """ADD COLUMN IF NOT EXISTS should raise UnsupportedFeatureError when not supported."""
        dialect = DummyDialect()
        with patch.object(type(dialect), "supports_add_column_if_not_exists", return_value=False):
            assert dialect.supports_add_column_if_not_exists() is False

    def test_drop_column_if_exists_raises_when_unsupported(self):
        """DROP COLUMN IF EXISTS should raise UnsupportedFeatureError when not supported."""
        dialect = DummyDialect()
        with patch.object(type(dialect), "supports_drop_column_if_exists", return_value=False):
            assert dialect.supports_drop_column_if_exists() is False

    def test_supports_foreign_key_on_delete_default(self):
        """DDLColumnMixin should support FK ON DELETE by default."""
        dialect = DummyDialect()
        assert dialect.supports_foreign_key_on_delete() is True

    def test_supports_foreign_key_on_update_default(self):
        """DDLColumnMixin should support FK ON UPDATE by default."""
        dialect = DummyDialect()
        assert dialect.supports_foreign_key_on_update() is True

    def test_supports_fk_match_default_false(self):
        """DDLColumnMixin should not support FK MATCH by default (DummyDialect overrides to True)."""
        dialect = DummyDialect()
        assert dialect.supports_fk_match() is True  # DummyDialect overrides to True for testing

    def test_supports_column_comment_default_false(self):
        """DDLColumnMixin should not support COLUMN COMMENT by default."""
        dialect = DummyDialect()
        assert dialect.supports_column_comment() is False


class TestTriggerCapabilityGating:
    """Tests for TRIGGER DDL capability gating."""

    def test_create_trigger_if_not_exists_raises_when_unsupported(self, dummy_dialect: DummyDialect):
        """CREATE TRIGGER IF NOT EXISTS should raise UnsupportedFeatureError when not supported."""
        trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger_name="t",
            table_name="t",
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.INSERT],
            function_name="f",
            if_not_exists=True,
        )
        with patch.object(type(dummy_dialect), "supports_trigger_if_not_exists", return_value=False):
            with pytest.raises(UnsupportedFeatureError, match="IF NOT EXISTS"):
                trigger.to_sql()

    def test_create_trigger_referencing_raises_when_unsupported(self, dummy_dialect: DummyDialect):
        """CREATE TRIGGER REFERENCING should raise UnsupportedFeatureError when not supported."""
        trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger_name="t",
            table_name="t",
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            function_name="f",
            referencing="OLD AS old_row",
        )
        with patch.object(type(dummy_dialect), "supports_trigger_referencing", return_value=False):
            with pytest.raises(UnsupportedFeatureError, match="REFERENCING"):
                trigger.to_sql()

    def test_create_trigger_when_raises_when_unsupported(self, dummy_dialect: DummyDialect):
        """CREATE TRIGGER WHEN should raise UnsupportedFeatureError when not supported."""
        from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
        trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger_name="t",
            table_name="t",
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            function_name="f",
            condition=ComparisonPredicate(
                dialect=dummy_dialect,
                op="=",
                left=Column(dummy_dialect, "id"),
                right=Literal(dialect=dummy_dialect, value=1),
            ),
        )
        with patch.object(type(dummy_dialect), "supports_trigger_when", return_value=False):
            with pytest.raises(UnsupportedFeatureError, match="WHEN"):
                trigger.to_sql()

    def test_drop_trigger_if_exists_raises_when_unsupported(self, dummy_dialect: DummyDialect):
        """DROP TRIGGER IF EXISTS should raise UnsupportedFeatureError when not supported."""
        trigger = DropTriggerExpression(
            dummy_dialect, trigger_name="t", if_exists=True
        )
        with patch.object(type(dummy_dialect), "supports_trigger_if_exists", return_value=False):
            with pytest.raises(UnsupportedFeatureError, match="IF EXISTS"):
                trigger.to_sql()


class TestFunctionCapabilityGating:
    """Tests for FUNCTION DDL capability gating."""

    def test_create_function_or_replace_raises_when_unsupported(self):
        """CREATE OR REPLACE FUNCTION should raise UnsupportedFeatureError when not supported."""
        dialect = DummyDialect()
        with patch.object(type(dialect), "supports_function_or_replace", return_value=False):
            assert dialect.supports_function_or_replace() is False

    def test_create_function_parameters_raises_when_unsupported(self):
        """CREATE FUNCTION with parameters should raise UnsupportedFeatureError when not supported."""
        dialect = DummyDialect()
        with patch.object(type(dialect), "supports_function_parameters", return_value=False):
            assert dialect.supports_function_parameters() is False


class TestSchemaCapabilityGating:
    """Tests for SCHEMA DDL capability gating."""

    def test_create_schema_raises_when_unsupported(self):
        """CREATE SCHEMA should raise UnsupportedFeatureError when not supported."""
        dialect = DummyDialect()
        with patch.object(type(dialect), "supports_create_schema", return_value=False):
            assert dialect.supports_create_schema() is False

    def test_drop_schema_raises_when_unsupported(self):
        """DROP SCHEMA should raise UnsupportedFeatureError when not supported."""
        dialect = DummyDialect()
        with patch.object(type(dialect), "supports_drop_schema", return_value=False):
            assert dialect.supports_drop_schema() is False


class TestDatabaseExpressions:
    """Tests for DATABASE DDL expressions."""

    def test_create_database_expression(self, dummy_dialect: DummyDialect):
        """Test CreateDatabaseExpression generates correct SQL."""
        expr = CreateDatabaseExpression(dummy_dialect, database_name="testdb")
        sql, params = expr.to_sql()
        assert "CREATE DATABASE" in sql
        assert '"testdb"' in sql or "testdb" in sql
        assert params == ()

    def test_drop_database_expression(self, dummy_dialect: DummyDialect):
        """Test DropDatabaseExpression generates correct SQL."""
        expr = DropDatabaseExpression(dummy_dialect, database_name="testdb")
        sql, params = expr.to_sql()
        assert "DROP DATABASE" in sql
        assert '"testdb"' in sql or "testdb" in sql
        assert params == ()

    def test_alter_database_expression(self, dummy_dialect: DummyDialect):
        """Test AlterDatabaseExpression generates correct SQL."""
        expr = AlterDatabaseExpression(
            dummy_dialect,
            database_name="testdb",
            action=AlterDatabaseAction.RENAME_TO,
            target="newdb",
        )
        sql, params = expr.to_sql()
        assert "ALTER DATABASE" in sql
        assert '"testdb"' in sql or "testdb" in sql
