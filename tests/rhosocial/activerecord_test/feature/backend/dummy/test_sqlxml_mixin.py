# tests/rhosocial/activerecord_test/feature/backend/dummy/test_sqlxml_mixin.py
"""Tests for SQL/XML expression support."""

import pytest

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.mixins import SQLXMLMixin
from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    OrderByClause,
    XMLParseDocumentType,
    XMLParseExpression,
    XMLPassingMechanism,
    XMLStandaloneOption,
    XMLTableColumn,
    xmlagg,
    xmlattributes,
    xmlcomment,
    xmlconcat,
    xmlelement,
    xmlexists,
    xmlforest,
    xmlparse,
    xmlpi,
    xmlquery,
    xmlroot,
    xmlserialize,
    xmltable,
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

    def test_xmlserialize_generates_standard_sql(self, dummy_dialect: DummyDialect):
        expr = xmlserialize(dummy_dialect, Column(dummy_dialect, "payload"), "VARCHAR(100)")

        sql, params = expr.to_sql()

        assert sql == 'XMLSERIALIZE(CONTENT "payload" AS VARCHAR(100))'
        assert params == ()

    def test_xmlelement_generates_standard_sql(self, dummy_dialect: DummyDialect):
        attrs = xmlattributes(dummy_dialect, ("42", "id"))
        expr = xmlelement(dummy_dialect, "item", "content", attributes=attrs)

        sql, params = expr.to_sql()

        assert sql == "XMLELEMENT(NAME item, XMLATTRIBUTES(? AS id), ?)"
        assert params == ("42", "content")

    def test_xmlforest_generates_standard_sql(self, dummy_dialect: DummyDialect):
        expr = xmlforest(dummy_dialect, (Column(dummy_dialect, "name"), "name"), ("x", "kind"))

        sql, params = expr.to_sql()

        assert sql == 'XMLFOREST("name" AS name, ? AS kind)'
        assert params == ("x",)

    def test_xmlconcat_generates_standard_sql(self, dummy_dialect: DummyDialect):
        expr = xmlconcat(dummy_dialect, Column(dummy_dialect, "left_xml"), "<right/>")

        sql, params = expr.to_sql()

        assert sql == 'XMLCONCAT("left_xml", ?)'
        assert params == ("<right/>",)

    def test_xmlcomment_generates_standard_sql(self, dummy_dialect: DummyDialect):
        expr = xmlcomment(dummy_dialect, "note")

        sql, params = expr.to_sql()

        assert sql == "XMLCOMMENT(?)"
        assert params == ("note",)

    def test_xmlpi_generates_standard_sql(self, dummy_dialect: DummyDialect):
        expr = xmlpi(dummy_dialect, "target", "instruction")

        sql, params = expr.to_sql()

        assert sql == "XMLPI(NAME target, ?)"
        assert params == ("instruction",)

    def test_xmlroot_generates_standard_sql(self, dummy_dialect: DummyDialect):
        expr = xmlroot(
            dummy_dialect,
            Column(dummy_dialect, "payload"),
            version="1.0",
            standalone=XMLStandaloneOption.NO,
        )

        sql, params = expr.to_sql()

        assert sql == 'XMLROOT("payload", VERSION ?, STANDALONE NO)'
        assert params == ("1.0",)

    def test_xmlagg_generates_standard_sql(self, dummy_dialect: DummyDialect):
        order_by = OrderByClause(dummy_dialect, [(Column(dummy_dialect, "id"), "ASC")])
        expr = xmlagg(dummy_dialect, Column(dummy_dialect, "payload"), order_by=order_by)

        sql, params = expr.to_sql()

        assert sql == 'XMLAGG("payload" ORDER BY "id" ASC)'
        assert params == ()

    def test_xmlquery_generates_standard_sql(self, dummy_dialect: DummyDialect):
        expr = xmlquery(
            dummy_dialect,
            "/root/item",
            passing=[Column(dummy_dialect, "payload")],
            passing_mechanism=XMLPassingMechanism.BY_REF,
        )

        sql, params = expr.to_sql()

        assert sql == 'XMLQUERY(? PASSING BY REF "payload" RETURNING CONTENT)'
        assert params == ("/root/item",)

    def test_xmlexists_generates_standard_sql(self, dummy_dialect: DummyDialect):
        expr = xmlexists(
            dummy_dialect,
            "/root/item",
            passing=[Column(dummy_dialect, "payload")],
        )

        sql, params = expr.to_sql()

        assert sql == 'XMLEXISTS(? PASSING "payload")'
        assert params == ("/root/item",)

    def test_xmltable_generates_standard_sql(self, dummy_dialect: DummyDialect):
        expr = xmltable(
            dummy_dialect,
            "/root/item",
            [
                XMLTableColumn("id", "INTEGER", path=Literal(dummy_dialect, "@id")),
                XMLTableColumn(
                    "name",
                    "VARCHAR(100)",
                    path=Literal(dummy_dialect, "name"),
                    default=Literal(dummy_dialect, "unknown"),
                ),
            ],
            passing=[Column(dummy_dialect, "payload")],
        )

        sql, params = expr.to_sql()

        assert sql == (
            'XMLTABLE(? PASSING "payload" COLUMNS ("id" INTEGER PATH ?, "name" VARCHAR(100) PATH ? DEFAULT ?))'
        )
        assert params == ("/root/item", "@id", "name", "unknown")

    @pytest.mark.parametrize(
        ("support_method", "expr", "feature"),
        [
            ("supports_xmlparse", lambda d: xmlparse(d, "<root/>"), "SQL/XML XMLPARSE"),
            ("supports_xmlserialize", lambda d: xmlserialize(d, "<root/>", "TEXT"), "SQL/XML XMLSERIALIZE"),
            ("supports_xmlattributes", lambda d: xmlattributes(d, ("1", "id")), "SQL/XML XMLATTRIBUTES"),
            ("supports_xmlelement", lambda d: xmlelement(d, "item"), "SQL/XML XMLELEMENT"),
            ("supports_xmlforest", lambda d: xmlforest(d, ("x", "item")), "SQL/XML XMLFOREST"),
            ("supports_xmlconcat", lambda d: xmlconcat(d, "<a/>", "<b/>"), "SQL/XML XMLCONCAT"),
            ("supports_xmlcomment", lambda d: xmlcomment(d, "note"), "SQL/XML XMLCOMMENT"),
            ("supports_xmlpi", lambda d: xmlpi(d, "target"), "SQL/XML XMLPI"),
            ("supports_xmlroot", lambda d: xmlroot(d, "<root/>"), "SQL/XML XMLROOT"),
            ("supports_xmlagg", lambda d: xmlagg(d, "<root/>"), "SQL/XML XMLAGG"),
            ("supports_xmlquery", lambda d: xmlquery(d, "/root"), "SQL/XML XMLQUERY"),
            ("supports_xmlexists", lambda d: xmlexists(d, "/root"), "SQL/XML XMLEXISTS"),
            ("supports_xmltable", lambda d: xmltable(d, "/root", []), "SQL/XML XMLTABLE"),
        ],
    )
    def test_sqlxml_mixin_defaults_to_unsupported(self, support_method, expr, feature):
        dialect = UnsupportedSQLXMLDialect()
        expression = expr(dialect)

        assert getattr(dialect, support_method)() is False
        with pytest.raises(UnsupportedFeatureError, match=feature):
            expression.to_sql()
