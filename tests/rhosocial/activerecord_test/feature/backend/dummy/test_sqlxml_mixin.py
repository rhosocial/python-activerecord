# tests/rhosocial/activerecord_test/feature/backend/dummy/test_sqlxml_mixin.py
"""Tests for SQL/XML expression support."""

import pytest

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.mixins import SQLXMLMixin
from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    XMLParseDocumentType,
    XMLParseExpression,
    xmlparse,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class UnsupportedSQLXMLDialect(SQLDialectBase, SQLXMLMixin):
    """Dialect using SQLXMLMixin defaults."""


class TestSQLXMLMixin:
    def test_xmlparse_factory_returns_expression(self, dummy_dialect: DummyDialect):
        expr = xmlparse(dummy_dialect, "<root/>")

        assert isinstance(expr, XMLParseExpression)
        assert expr.document_type is XMLParseDocumentType.DOCUMENT
        assert isinstance(expr.content, Literal)

    def test_xmlparse_document_generates_standard_sql(self, dummy_dialect: DummyDialect):
        expr = xmlparse(dummy_dialect, "<root/>")

        sql, params = expr.to_sql()

        assert sql == "XMLPARSE(DOCUMENT ?)"
        assert params == ("<root/>",)

    def test_xmlparse_content_generates_standard_sql(self, dummy_dialect: DummyDialect):
        expr = xmlparse(dummy_dialect, "text <child/>", document=False)

        sql, params = expr.to_sql()

        assert sql == "XMLPARSE(CONTENT ?)"
        assert params == ("text <child/>",)

    def test_xmlparse_preserve_whitespace_generates_standard_sql(
        self,
        dummy_dialect: DummyDialect,
    ):
        expr = xmlparse(dummy_dialect, "<root/>", preserve_whitespace=True)

        sql, params = expr.to_sql()

        assert sql == "XMLPARSE(DOCUMENT ? PRESERVE WHITESPACE)"
        assert params == ("<root/>",)

    def test_xmlparse_accepts_expression_content(self, dummy_dialect: DummyDialect):
        expr = xmlparse(dummy_dialect, Column(dummy_dialect, "payload"))

        sql, params = expr.to_sql()

        assert sql == 'XMLPARSE(DOCUMENT "payload")'
        assert params == ()

    def test_xmlparse_expression_can_be_constructed_directly(self, dummy_dialect: DummyDialect):
        expr = XMLParseExpression(
            dummy_dialect,
            Literal(dummy_dialect, "<root/>"),
            XMLParseDocumentType.CONTENT,
        )

        sql, params = expr.to_sql()

        assert sql == "XMLPARSE(CONTENT ?)"
        assert params == ("<root/>",)

    def test_sqlxml_mixin_defaults_to_unsupported(self):
        dialect = UnsupportedSQLXMLDialect()
        expr = xmlparse(dialect, "<root/>")

        assert dialect.supports_xmlparse() is False
        with pytest.raises(UnsupportedFeatureError, match="SQL/XML XMLPARSE"):
            expr.to_sql()
