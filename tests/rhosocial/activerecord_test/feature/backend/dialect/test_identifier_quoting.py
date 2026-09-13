# tests/rhosocial/activerecord_test/feature/backend/dialect/test_identifier_quoting.py
"""
Test for identifier quoting feature.

Covers:
- IdentifierQuotingWarning class
- SQLDialectBase.format_identifier (quoting, escaping, need_quote)
- SQLDialectBase.is_reserved_word (case-insensitive)
- Reserved word warning emission
- Per-role need_quote properties on Column, TableExpression,
  QualifiedIdentifierExpression, WildcardExpression, Identifier
- Format methods (format_column, format_table, format_wildcard,
  format_identifier_expression, format_qualified_identifier)
"""

import warnings

import pytest

from rhosocial.activerecord.backend.warnings import IdentifierQuotingWarning
from rhosocial.activerecord.backend.expression.core import (
    Column,
    TableExpression,
    QualifiedIdentifierExpression,
    WildcardExpression,
)
from rhosocial.activerecord.backend.expression.literals import Identifier
from rhosocial.activerecord.backend.impl.dummy import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestIdentifierQuotingWarning:
    """Test IdentifierQuotingWarning class."""

    def test_is_user_warning_subclass(self):
        assert issubclass(IdentifierQuotingWarning, UserWarning)

    def test_can_be_raised(self):
        with pytest.warns(IdentifierQuotingWarning):
            warnings.warn("test", IdentifierQuotingWarning)


class TestSQLDialectBaseIdentifierQuoting:
    """Test base dialect format_identifier and reserved words."""

    def test_format_identifier_default_quotes(self):
        d = SQLiteDialect()
        assert d.format_identifier("users") == '"users"'

    def test_format_identifier_need_quote_false_returns_raw(self):
        d = SQLiteDialect()
        assert d.format_identifier("users", need_quote=False) == "users"

    def test_format_identifier_escapes_internal_quotes(self):
        d = SQLiteDialect()
        assert d.format_identifier('my"table') == '"my""table"'

    def test_format_identifier_need_quote_false_no_escaping(self):
        d = SQLiteDialect()
        assert d.format_identifier('my"table', need_quote=False) == 'my"table'

    def test_reserved_words_is_frozenset(self):
        d = SQLiteDialect()
        assert isinstance(d.reserved_words, frozenset)

    def test_reserved_words_not_empty(self):
        d = SQLiteDialect()
        assert len(d.reserved_words) > 0

    def test_is_reserved_word_case_insensitive(self):
        d = SQLiteDialect()
        assert d.is_reserved_word("SELECT") is True
        assert d.is_reserved_word("select") is True
        assert d.is_reserved_word("Select") is True

    def test_is_reserved_word_non_reserved(self):
        d = SQLiteDialect()
        assert d.is_reserved_word("users") is False

    def test_reserved_word_warning_emitted(self):
        d = SQLiteDialect()
        with pytest.warns(IdentifierQuotingWarning, match="select"):
            d.format_identifier("select", need_quote=False)

    def test_no_warning_for_non_reserved_word(self):
        d = SQLiteDialect()
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            d.format_identifier("users", need_quote=False)

    def test_format_identifier_default_quotes_dummy(self):
        d = DummyDialect()
        assert d.format_identifier("users") == '"users"'

    def test_format_identifier_need_quote_false_dummy(self):
        d = DummyDialect()
        assert d.format_identifier("users", need_quote=False) == "users"

    def test_format_identifier_escapes_internal_quotes_dummy(self):
        d = DummyDialect()
        assert d.format_identifier('col"name') == '"col""name"'

    def test_reserved_words_empty_dummy(self):
        d = DummyDialect()
        assert len(d.reserved_words) == 0

    def test_is_reserved_word_false_dummy(self):
        d = DummyDialect()
        assert d.is_reserved_word("select") is False


class TestColumnIdentifierQuoting:
    """Test Column per-role need_quote properties."""

    def test_defaults_all_true(self):
        d = SQLiteDialect()
        col = Column(d, "id", table="users")
        assert col.name_need_quote is True
        assert col.table_need_quote is True
        assert col.schema_need_quote is True
        assert col.alias_need_quote is True

    def test_all_false(self):
        d = SQLiteDialect()
        col = Column(d, "id", table="users",
                     name_need_quote=False, table_need_quote=False,
                     schema_need_quote=False, alias_need_quote=False)
        assert col.name_need_quote is False
        assert col.table_need_quote is False
        assert col.schema_need_quote is False
        assert col.alias_need_quote is False

    def test_alias_need_quote_independent(self):
        d = SQLiteDialect()
        col = Column(d, "id", name_need_quote=True, alias_need_quote=False)
        assert col.name_need_quote is True
        assert col.alias_need_quote is False

    def test_schema_need_quote_independent(self):
        d = SQLiteDialect()
        col = Column(d, "id", table="t", schema_name="s",
                     name_need_quote=True, schema_need_quote=False)
        assert col.schema_need_quote is False
        assert col.table_need_quote is True
        assert col.name_need_quote is True

    def test_table_need_quote_independent(self):
        d = SQLiteDialect()
        col = Column(d, "id", table="t",
                     name_need_quote=True, table_need_quote=False)
        assert col.table_need_quote is False
        assert col.name_need_quote is True

    def test_mixed_quoting(self):
        d = SQLiteDialect()
        col = Column(d, "id", table="t",
                     name_need_quote=False, table_need_quote=True)
        assert col.table_need_quote is True
        assert col.name_need_quote is False


class TestTableExpressionIdentifierQuoting:
    """Test TableExpression per-role need_quote properties."""

    def test_defaults_all_true(self):
        d = SQLiteDialect()
        t = TableExpression(d, "users")
        assert t.name_need_quote is True
        assert t.schema_need_quote is True
        assert t.alias_need_quote is True

    def test_all_false(self):
        d = SQLiteDialect()
        t = TableExpression(d, "users",
                            name_need_quote=False, schema_need_quote=False,
                            alias_need_quote=False)
        assert t.name_need_quote is False
        assert t.schema_need_quote is False
        assert t.alias_need_quote is False

    def test_schema_need_quote_independent(self):
        d = SQLiteDialect()
        t = TableExpression(d, "users", schema_name="public",
                            name_need_quote=True, schema_need_quote=False)
        assert t.schema_need_quote is False
        assert t.name_need_quote is True

    def test_alias_need_quote_independent(self):
        d = SQLiteDialect()
        t = TableExpression(d, "users",
                            name_need_quote=True, alias_need_quote=False)
        assert t.name_need_quote is True
        assert t.alias_need_quote is False


class TestQualifiedIdentifierExpressionIdentifierQuoting:
    """Test QualifiedIdentifierExpression per-role need_quote properties."""

    def test_defaults_all_true(self):
        d = SQLiteDialect()
        qi = QualifiedIdentifierExpression(d, schema="public", name="users")
        assert qi.name_need_quote is True
        assert qi.schema_need_quote is True

    def test_all_false(self):
        d = SQLiteDialect()
        qi = QualifiedIdentifierExpression(d, schema="public", name="users",
                                           name_need_quote=False,
                                           schema_need_quote=False)
        assert qi.name_need_quote is False
        assert qi.schema_need_quote is False

    def test_schema_need_quote_independent(self):
        d = SQLiteDialect()
        qi = QualifiedIdentifierExpression(d, schema="public", name="users",
                                           name_need_quote=True,
                                           schema_need_quote=False)
        assert qi.schema_need_quote is False
        assert qi.name_need_quote is True

    def test_no_schema(self):
        d = SQLiteDialect()
        qi = QualifiedIdentifierExpression(d, name="users",
                                           name_need_quote=False)
        assert qi.name_need_quote is False


class TestWildcardExpressionIdentifierQuoting:
    """Test WildcardExpression per-role need_quote properties."""

    def test_defaults_all_true(self):
        d = SQLiteDialect()
        w = WildcardExpression(d, table="users")
        assert w.table_need_quote is True
        assert w.schema_need_quote is True

    def test_all_false(self):
        d = SQLiteDialect()
        w = WildcardExpression(d, table="users",
                               table_need_quote=False, schema_need_quote=False)
        assert w.table_need_quote is False
        assert w.schema_need_quote is False

    def test_table_need_quote_independent(self):
        d = SQLiteDialect()
        w = WildcardExpression(d, table="users", schema_name="public",
                               table_need_quote=False, schema_need_quote=True)
        assert w.table_need_quote is False
        assert w.schema_need_quote is True

    def test_schema_need_quote_independent(self):
        d = SQLiteDialect()
        w = WildcardExpression(d, table="users", schema_name="public",
                               table_need_quote=True, schema_need_quote=False)
        assert w.schema_need_quote is False
        assert w.table_need_quote is True


class TestIdentifierIdentifierQuoting:
    """Test Identifier per-role need_quote properties."""

    def test_defaults_all_true(self):
        d = SQLiteDialect()
        ident = Identifier(d, "users")
        assert ident.name_need_quote is True
        assert ident.alias_need_quote is True

    def test_all_false(self):
        d = SQLiteDialect()
        ident = Identifier(d, "users",
                           name_need_quote=False, alias_need_quote=False)
        assert ident.name_need_quote is False
        assert ident.alias_need_quote is False

    def test_alias_need_quote_independent(self):
        d = SQLiteDialect()
        ident = Identifier(d, "users",
                           name_need_quote=True, alias_need_quote=False)
        assert ident.name_need_quote is True
        assert ident.alias_need_quote is False


class TestFormatMethodDirectPropertyAccess:
    """Test that format methods read need_quote properties directly.

    Uses DummyDialect because SQLite's SQLiteIdentifierMixin overrides
    format_column/format_wildcard to always quote, whereas DummyDialect
    inherits the generic ExpressionMixin that reads the properties.
    """

    def test_format_column_unquoted(self):
        d = DummyDialect()
        col = Column(d, "id", table="users", name_need_quote=False,
                     table_need_quote=False)
        sql, params = d.format_column(col)
        assert sql == "users.id"
        assert params == ()

    def test_format_column_with_alias(self):
        d = DummyDialect()
        col = Column(d, "id", table="users", alias="user_id",
                     name_need_quote=False, table_need_quote=False,
                     alias_need_quote=False)
        sql, params = d.format_column(col)
        assert sql == "users.id AS user_id"

    def test_format_column_alias_independent_quoting(self):
        d = DummyDialect()
        col = Column(d, "id", table="users", alias="user_id",
                     name_need_quote=True, table_need_quote=True,
                     alias_need_quote=False)
        sql, params = d.format_column(col)
        assert sql == '"users"."id" AS user_id'

    def test_format_column_schema_table_name(self):
        d = DummyDialect()
        col = Column(d, "id", table="users", schema_name="public",
                     name_need_quote=False, table_need_quote=False,
                     schema_need_quote=False)
        sql, params = d.format_column(col)
        assert sql == "public.users.id"

    def test_format_column_schema_table_name_quoted(self):
        d = DummyDialect()
        col = Column(d, "id", table="users", schema_name="public",
                     name_need_quote=True, table_need_quote=True,
                     schema_need_quote=True)
        sql, params = d.format_column(col)
        assert sql == '"public"."users"."id"'

    def test_format_column_name_only(self):
        d = DummyDialect()
        col = Column(d, "id", name_need_quote=False)
        sql, params = d.format_column(col)
        assert sql == "id"

    def test_format_column_name_only_quoted(self):
        d = DummyDialect()
        col = Column(d, "id", name_need_quote=True)
        sql, params = d.format_column(col)
        assert sql == '"id"'

    def test_format_table_unquoted(self):
        d = DummyDialect()
        t = TableExpression(d, "users", name_need_quote=False)
        sql, params = d.format_table(t)
        assert sql == "users"

    def test_format_table_with_alias(self):
        d = DummyDialect()
        t = TableExpression(d, "users", alias="u",
                            name_need_quote=False, alias_need_quote=False)
        sql, params = d.format_table(t)
        assert sql == "users AS u"

    def test_format_table_schema_quoted(self):
        d = DummyDialect()
        t = TableExpression(d, "users", schema_name="public",
                            name_need_quote=True, schema_need_quote=True)
        sql, params = d.format_table(t)
        assert sql == '"public"."users"'

    def test_format_table_schema_unquoted(self):
        d = DummyDialect()
        t = TableExpression(d, "users", schema_name="public",
                            name_need_quote=False, schema_need_quote=False)
        sql, params = d.format_table(t)
        assert sql == "public.users"

    def test_format_table_alias_independent_quoting(self):
        d = DummyDialect()
        t = TableExpression(d, "users", alias="u",
                            name_need_quote=True, alias_need_quote=False)
        sql, params = d.format_table(t)
        assert sql == '"users" AS u'

    def test_format_wildcard_unquoted(self):
        d = DummyDialect()
        w = WildcardExpression(d, table="users", table_need_quote=False)
        sql, params = d.format_wildcard(w)
        assert sql == "users.*"

    def test_format_wildcard_quoted(self):
        d = DummyDialect()
        w = WildcardExpression(d, table="users", table_need_quote=True)
        sql, params = d.format_wildcard(w)
        assert sql == '"users".*'

    def test_format_wildcard_no_table(self):
        d = DummyDialect()
        w = WildcardExpression(d)
        sql, params = d.format_wildcard(w)
        assert sql == "*"

    def test_format_wildcard_schema_and_table(self):
        d = DummyDialect()
        w = WildcardExpression(d, table="users", schema_name="public",
                               table_need_quote=False, schema_need_quote=False)
        sql, params = d.format_wildcard(w)
        assert sql == "public.users.*"

    def test_format_wildcard_schema_and_table_quoted(self):
        d = DummyDialect()
        w = WildcardExpression(d, table="users", schema_name="public",
                               table_need_quote=True, schema_need_quote=True)
        sql, params = d.format_wildcard(w)
        assert sql == '"public"."users".*'

    def test_format_identifier_expression_unquoted(self):
        d = DummyDialect()
        ident = Identifier(d, "users", name_need_quote=False)
        sql, params = d.format_identifier_expression(ident)
        assert sql == "users"

    def test_format_identifier_expression_quoted(self):
        d = DummyDialect()
        ident = Identifier(d, "users", name_need_quote=True)
        sql, params = d.format_identifier_expression(ident)
        assert sql == '"users"'

    def test_format_column_reserved_word_quoted(self):
        d = DummyDialect()
        col = Column(d, "select", table="users", name_need_quote=True)
        sql, params = d.format_column(col)
        assert sql == '"users"."select"'

    def test_format_column_reserved_word_unquoted_warning(self):
        d = DummyDialect()
        d._reserved_words = frozenset({"select"})
        col = Column(d, "select", table="users", name_need_quote=False,
                     table_need_quote=False)
        with pytest.warns(IdentifierQuotingWarning):
            sql, params = d.format_column(col)
        assert sql == "users.select"

    def test_format_identifier_expression_reserved_word_warning(self):
        d = DummyDialect()
        d._reserved_words = frozenset({"select"})
        ident = Identifier(d, "select", name_need_quote=False)
        with pytest.warns(IdentifierQuotingWarning):
            sql, params = d.format_identifier_expression(ident)
        assert sql == "select"

    def test_format_qualified_identifier_unquoted(self):
        d = DummyDialect()
        qi = QualifiedIdentifierExpression(d, schema="public", name="users",
                                           name_need_quote=False,
                                           schema_need_quote=False)
        sql, params = d.format_qualified_identifier(qi)
        assert sql == "public.users"

    def test_format_qualified_identifier_quoted(self):
        d = DummyDialect()
        qi = QualifiedIdentifierExpression(d, schema="public", name="users",
                                           name_need_quote=True,
                                           schema_need_quote=True)
        sql, params = d.format_qualified_identifier(qi)
        assert sql == '"public"."users"'

    def test_format_qualified_identifier_no_schema(self):
        d = DummyDialect()
        qi = QualifiedIdentifierExpression(d, name="users",
                                           name_need_quote=False)
        sql, params = d.format_qualified_identifier(qi)
        assert sql == "users"

    def test_format_column_mixed_quoting(self):
        d = DummyDialect()
        col = Column(d, "id", table="users", schema_name="public",
                     name_need_quote=True, table_need_quote=False,
                     schema_need_quote=False)
        sql, params = d.format_column(col)
        assert sql == 'public.users."id"'

    def test_format_table_mixed_quoting(self):
        d = DummyDialect()
        t = TableExpression(d, "users", schema_name="public",
                            name_need_quote=True, schema_need_quote=False)
        sql, params = d.format_table(t)
        assert sql == 'public."users"'

    def test_format_wildcard_table_need_quote_independent(self):
        d = DummyDialect()
        w = WildcardExpression(d, table="users", schema_name="public",
                               table_need_quote=False, schema_need_quote=True)
        sql, params = d.format_wildcard(w)
        assert sql == '"public".users.*'
