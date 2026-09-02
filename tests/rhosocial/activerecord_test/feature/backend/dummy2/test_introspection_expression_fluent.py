# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_introspection_expression_fluent.py
"""
Cover IntrospectionExpression fluent API surface and dialect delegation.

Targets previously untested branches in backend/expression/introspection.py:
- schema()/include_views()/include_system()/table_type() fluent setters
- to_sql() delegation for every introspection expression class
- get_params() reflection over __init__ signature (param -> _attr convention)
"""

import pytest

from rhosocial.activerecord.backend.expression.introspection import (
    DatabaseInfoExpression,
    TableListExpression,
    TableInfoExpression,
    ColumnInfoExpression,
    IndexInfoExpression,
    ForeignKeyExpression,
    TriggerListExpression,
    TriggerInfoExpression,
)


@pytest.fixture
def dialect(dummy_dialect):
    return dummy_dialect


class TestTableListExpression:
    def test_fluent_chain_all_setters(self, dialect):
        expr = (
            TableListExpression(dialect)
            .schema("main")
            .include_views(False)
            .include_system(True)
            .table_type("VIEW")
        )
        params = expr.get_params()
        assert params["schema"] == "main"
        assert params["include_views"] is False
        assert params["include_system"] is True
        assert params["table_type"] == "VIEW"

    def test_unsupported_raises(self, dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        with pytest.raises(UnsupportedFeatureError):
            TableListExpression(dialect, schema="main").to_sql()

    def test_constructor_kwargs_roundtrip(self, dialect):
        expr = TableListExpression(
            dialect, schema="s1", include_views=False, include_system=True
        )
        params = expr.get_params()
        assert params["schema"] == "s1"
        assert params["include_views"] is False


class TestTableInfoExpression:
    def test_all_include_flags(self, dialect):
        expr = (
            TableInfoExpression(dialect, "users", schema="main")
            .include_columns(False)
            .include_indexes(False)
            .include_foreign_keys(False)
        )
        params = expr.get_params()
        assert params["table"] == "users"
        assert params["include_columns"] is False
        assert params["include_indexes"] is False
        assert params["include_foreign_keys"] is False

    def test_table_setter_overrides(self, dialect):
        expr = TableInfoExpression(dialect, "old").table("new")
        assert expr.get_params()["table"] == "new"

    def test_unsupported_raises(self, dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        with pytest.raises(UnsupportedFeatureError):
            TableInfoExpression(dialect, "users").to_sql()


class TestColumnInfoExpression:
    def test_include_hidden_setter(self, dialect):
        expr = ColumnInfoExpression(dialect, "users").include_hidden(True)
        assert expr.get_params()["include_hidden"] is True

    def test_table_setter(self, dialect):
        expr = ColumnInfoExpression(dialect, "old").table("new")
        assert expr.get_params()["table"] == "new"

    def test_unsupported_raises(self, dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        with pytest.raises(UnsupportedFeatureError):
            ColumnInfoExpression(dialect, "users").to_sql()


class TestIndexInfoExpression:
    def test_table_setter(self, dialect):
        expr = IndexInfoExpression(dialect, "old").table("new")
        assert expr.get_params()["table"] == "new"

    def test_unsupported_raises(self, dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        with pytest.raises(UnsupportedFeatureError):
            IndexInfoExpression(dialect, "users").to_sql()


class TestForeignKeyExpression:
    def test_table_setter(self, dialect):
        expr = ForeignKeyExpression(dialect, "old").table("new")
        assert expr.get_params()["table"] == "new"

    def test_unsupported_raises(self, dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        with pytest.raises(UnsupportedFeatureError):
            ForeignKeyExpression(dialect, "users").to_sql()


class TestTriggerExpressions:
    def test_trigger_list_for_table(self, dialect):
        expr = TriggerListExpression(dialect, schema="main").for_table("users")
        params = expr.get_params()
        assert params["schema"] == "main"
        assert params["table"] == "users"

    def test_trigger_list_unsupported_raises(self, dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        with pytest.raises(UnsupportedFeatureError):
            TriggerListExpression(dialect).to_sql()

    def test_trigger_info_trigger_setter(self, dialect):
        expr = TriggerInfoExpression(dialect, "old").trigger("new")
        assert expr.get_params()["trigger"] == "new"

    def test_trigger_info_unsupported_raises(self, dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        with pytest.raises(UnsupportedFeatureError):
            TriggerInfoExpression(dialect, "trg").to_sql()


class TestDatabaseInfoExpression:
    def test_unsupported_raises(self, dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        if DatabaseInfoExpression(dialect) is None:  # pragma: no cover
            raise AssertionError
        with pytest.raises(UnsupportedFeatureError):
            DatabaseInfoExpression(dialect).to_sql()


class TestBaseNotImplemented:
    def test_base_class_to_sql_raises(self, dialect):
        with pytest.raises(NotImplementedError):
            IntrospectionBase = TableListExpression.__mro__[1]
            IntrospectionBase(dialect).to_sql()
