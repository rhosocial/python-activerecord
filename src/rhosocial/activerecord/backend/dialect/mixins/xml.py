# src/rhosocial/activerecord/backend/dialect/mixins/xml.py
import re
from typing import List, Optional, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.xml import (
        XMLAggExpression,
        XMLAttributesExpression,
        XMLCommentExpression,
        XMLConcatExpression,
        XMLElementExpression,
        XMLExistsExpression,
        XMLForestExpression,
        XMLParseExpression,
        XMLPassingMechanism,
        XMLPIExpression,
        XMLQueryExpression,
        XMLRootExpression,
        XMLSerializeExpression,
        XMLTableExpression,
    )
    from ...expression.bases import BaseExpression


class SQLXMLParsingMixin:
    """Mixin for SQL/XML parsing support."""

    def supports_xmlparse(self) -> bool:
        """Whether SQL/XML XMLPARSE is supported."""
        return False

    def format_xmlparse_expression(
        self,
        expr: "XMLParseExpression",
    ) -> Tuple[str, tuple]:
        """Format a SQL/XML XMLPARSE expression."""
        if not self.supports_xmlparse():
            raise UnsupportedFeatureError(self.name, "SQL/XML XMLPARSE")
        content_sql, params = expr.content.to_sql()
        sql = f"XMLPARSE({expr.document_type.value} {content_sql}"
        if expr.whitespace_option is not None:
            sql += f" {expr.whitespace_option.value}"
        return f"{sql})", params


class SQLXMLSerializationMixin:
    """Mixin for SQL/XML serialization support."""

    def supports_xmlserialize(self) -> bool:
        """Whether SQL/XML XMLSERIALIZE is supported."""
        return False

    def format_xmlserialize_expression(
        self,
        expr: "XMLSerializeExpression",
    ) -> Tuple[str, tuple]:
        """Format a SQL/XML XMLSERIALIZE expression."""
        if not self.supports_xmlserialize():
            raise UnsupportedFeatureError(self.name, "SQL/XML XMLSERIALIZE")
        if not self._validate_data_type(expr.target_type):
            raise ValueError(f"Invalid XMLSERIALIZE target type: {expr.target_type}")
        content_sql, params = expr.content.to_sql()
        parts = [expr.document_type.value, content_sql, "AS", expr.target_type]
        if expr.whitespace_option is not None:
            parts.append(expr.whitespace_option.value)
        return f"XMLSERIALIZE({' '.join(parts)})", params


class SQLXMLConstructionMixin:
    """Mixin for SQL/XML construction support."""

    _XML_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:-]*$")

    def supports_xmlelement(self) -> bool:
        """Whether SQL/XML XMLELEMENT is supported."""
        return False

    def supports_xmlattributes(self) -> bool:
        """Whether SQL/XML XMLATTRIBUTES is supported."""
        return False

    def supports_xmlforest(self) -> bool:
        """Whether SQL/XML XMLFOREST is supported."""
        return False

    def supports_xmlconcat(self) -> bool:
        """Whether SQL/XML XMLCONCAT is supported."""
        return False

    def supports_xmlcomment(self) -> bool:
        """Whether SQL/XML XMLCOMMENT is supported."""
        return False

    def supports_xmlpi(self) -> bool:
        """Whether SQL/XML XMLPI is supported."""
        return False

    def supports_xmlroot(self) -> bool:
        """Whether SQL/XML XMLROOT is supported."""
        return False

    def format_xml_name(self, name: str) -> str:
        """Validate and format an SQL/XML name token."""
        if not self._XML_NAME_PATTERN.fullmatch(name):
            raise ValueError(f"Invalid SQL/XML name: {name}")
        return name

    def format_xmlattributes_expression(
        self,
        expr: "XMLAttributesExpression",
    ) -> Tuple[str, tuple]:
        """Format a SQL/XML XMLATTRIBUTES clause."""
        if not self.supports_xmlattributes():
            raise UnsupportedFeatureError(self.name, "SQL/XML XMLATTRIBUTES")
        parts = []
        all_params = []
        for attribute in expr.attributes:
            value_sql, value_params = attribute.value.to_sql()
            part = value_sql
            if attribute.name is not None:
                part += f" AS {self.format_xml_name(attribute.name)}"
            parts.append(part)
            all_params.extend(value_params)
        return f"XMLATTRIBUTES({', '.join(parts)})", tuple(all_params)

    def format_xmlelement_expression(
        self,
        expr: "XMLElementExpression",
    ) -> Tuple[str, tuple]:
        """Format a SQL/XML XMLELEMENT expression."""
        if not self.supports_xmlelement():
            raise UnsupportedFeatureError(self.name, "SQL/XML XMLELEMENT")
        parts = [f"NAME {self.format_xml_name(expr.name)}"]
        all_params = []
        if expr.attributes is not None:
            attributes_sql, attributes_params = expr.attributes.to_sql()
            parts.append(attributes_sql)
            all_params.extend(attributes_params)
        for item in expr.content:
            item_sql, item_params = item.to_sql()
            parts.append(item_sql)
            all_params.extend(item_params)
        return f"XMLELEMENT({', '.join(parts)})", tuple(all_params)

    def format_xmlforest_expression(
        self,
        expr: "XMLForestExpression",
    ) -> Tuple[str, tuple]:
        """Format a SQL/XML XMLFOREST expression."""
        if not self.supports_xmlforest():
            raise UnsupportedFeatureError(self.name, "SQL/XML XMLFOREST")
        parts = []
        all_params = []
        for item in expr.items:
            value_sql, value_params = item.value.to_sql()
            part = value_sql
            if item.name is not None:
                part += f" AS {self.format_xml_name(item.name)}"
            parts.append(part)
            all_params.extend(value_params)
        return f"XMLFOREST({', '.join(parts)})", tuple(all_params)

    def format_xmlconcat_expression(
        self,
        expr: "XMLConcatExpression",
    ) -> Tuple[str, tuple]:
        """Format a SQL/XML XMLCONCAT expression."""
        if not self.supports_xmlconcat():
            raise UnsupportedFeatureError(self.name, "SQL/XML XMLCONCAT")
        parts = []
        all_params = []
        for part in expr.parts:
            part_sql, part_params = part.to_sql()
            parts.append(part_sql)
            all_params.extend(part_params)
        return f"XMLCONCAT({', '.join(parts)})", tuple(all_params)

    def format_xmlcomment_expression(
        self,
        expr: "XMLCommentExpression",
    ) -> Tuple[str, tuple]:
        """Format a SQL/XML XMLCOMMENT expression."""
        if not self.supports_xmlcomment():
            raise UnsupportedFeatureError(self.name, "SQL/XML XMLCOMMENT")
        content_sql, params = expr.content.to_sql()
        return f"XMLCOMMENT({content_sql})", params

    def format_xmlpi_expression(self, expr: "XMLPIExpression") -> Tuple[str, tuple]:
        """Format a SQL/XML XMLPI expression."""
        if not self.supports_xmlpi():
            raise UnsupportedFeatureError(self.name, "SQL/XML XMLPI")
        sql = f"XMLPI(NAME {self.format_xml_name(expr.target)}"
        if expr.content is None:
            return f"{sql})", ()
        content_sql, params = expr.content.to_sql()
        return f"{sql}, {content_sql})", params

    def format_xmlroot_expression(
        self,
        expr: "XMLRootExpression",
    ) -> Tuple[str, tuple]:
        """Format a SQL/XML XMLROOT expression."""
        if not self.supports_xmlroot():
            raise UnsupportedFeatureError(self.name, "SQL/XML XMLROOT")
        content_sql, all_params = expr.content.to_sql()
        parts = [content_sql]
        params = list(all_params)
        if expr.version is not None:
            version_sql, version_params = expr.version.to_sql()
            parts.append(f"VERSION {version_sql}")
            params.extend(version_params)
        if expr.standalone is not None:
            parts.append(f"STANDALONE {expr.standalone.value}")
        return f"XMLROOT({', '.join(parts)})", tuple(params)


class SQLXMLAggregationMixin:
    """Mixin for SQL/XML aggregation support."""

    def supports_xmlagg(self) -> bool:
        """Whether SQL/XML XMLAGG is supported."""
        return False

    def format_xmlagg_expression(self, expr: "XMLAggExpression") -> Tuple[str, tuple]:
        """Format a SQL/XML XMLAGG expression."""
        if not self.supports_xmlagg():
            raise UnsupportedFeatureError(self.name, "SQL/XML XMLAGG")
        expression_sql, params = expr.expression.to_sql()
        sql = expression_sql
        all_params = list(params)
        if expr.order_by is not None:
            order_sql, order_params = expr.order_by.to_sql()
            sql = f"{sql} {order_sql}"
            all_params.extend(order_params)
        return f"XMLAGG({sql})", tuple(all_params)


class SQLXMLQueryingMixin:
    """Mixin for SQL/XML querying support."""

    def supports_xmlquery(self) -> bool:
        """Whether SQL/XML XMLQUERY is supported."""
        return False

    def supports_xmlexists(self) -> bool:
        """Whether SQL/XML XMLEXISTS is supported."""
        return False

    def supports_xmltable(self) -> bool:
        """Whether SQL/XML XMLTABLE is supported."""
        return False

    def _format_xml_passing_clause(
        self,
        expressions: List["BaseExpression"],
        mechanism: Optional["XMLPassingMechanism"] = None,
    ) -> Tuple[str, tuple]:
        if not expressions:
            return "", ()
        all_params = []
        parts = []
        for expression in expressions:
            expr_sql, expr_params = expression.to_sql()
            parts.append(expr_sql)
            all_params.extend(expr_params)
        prefix = "PASSING"
        if mechanism is not None:
            prefix += f" {mechanism.value}"
        return f"{prefix} {', '.join(parts)}", tuple(all_params)

    def format_xmlquery_expression(
        self,
        expr: "XMLQueryExpression",
    ) -> Tuple[str, tuple]:
        """Format a SQL/XML XMLQUERY expression."""
        if not self.supports_xmlquery():
            raise UnsupportedFeatureError(self.name, "SQL/XML XMLQUERY")
        query_sql, query_params = expr.query.to_sql()
        parts = [query_sql]
        all_params = list(query_params)
        passing_sql, passing_params = self._format_xml_passing_clause(
            expr.passing,
            expr.passing_mechanism,
        )
        if passing_sql:
            parts.append(passing_sql)
            all_params.extend(passing_params)
        if expr.returning_content:
            parts.append("RETURNING CONTENT")
        if expr.empty_handling is not None:
            parts.append(expr.empty_handling.value)
        return f"XMLQUERY({' '.join(parts)})", tuple(all_params)

    def format_xmlexists_expression(
        self,
        expr: "XMLExistsExpression",
    ) -> Tuple[str, tuple]:
        """Format a SQL/XML XMLEXISTS predicate."""
        if not self.supports_xmlexists():
            raise UnsupportedFeatureError(self.name, "SQL/XML XMLEXISTS")
        query_sql, query_params = expr.query.to_sql()
        parts = [query_sql]
        all_params = list(query_params)
        passing_sql, passing_params = self._format_xml_passing_clause(
            expr.passing,
            expr.passing_mechanism,
        )
        if passing_sql:
            parts.append(passing_sql)
            all_params.extend(passing_params)
        return f"XMLEXISTS({' '.join(parts)})", tuple(all_params)

    def format_xmltable_expression(
        self,
        expr: "XMLTableExpression",
    ) -> Tuple[str, tuple]:
        """Format a SQL/XML XMLTABLE expression."""
        if not self.supports_xmltable():
            raise UnsupportedFeatureError(self.name, "SQL/XML XMLTABLE")
        row_sql, row_params = expr.row_pattern.to_sql()
        parts = [row_sql]
        all_params = list(row_params)
        passing_sql, passing_params = self._format_xml_passing_clause(
            expr.passing,
            expr.passing_mechanism,
        )
        if passing_sql:
            parts.append(passing_sql)
            all_params.extend(passing_params)
        column_parts = []
        for column in expr.columns:
            if not self._validate_data_type(column.data_type):
                raise ValueError(f"Invalid XMLTABLE column type: {column.data_type}")
            column_sql = f"{self.format_identifier(column.name)} {column.data_type}"
            if column.path is not None:
                path_sql, path_params = column.path.to_sql()
                column_sql += f" PATH {path_sql}"
                all_params.extend(path_params)
            if column.default is not None:
                default_sql, default_params = column.default.to_sql()
                column_sql += f" DEFAULT {default_sql}"
                all_params.extend(default_params)
            column_parts.append(column_sql)
        parts.append(f"COLUMNS ({', '.join(column_parts)})")
        return f"XMLTABLE({' '.join(parts)})", tuple(all_params)


class SQLXMLMixin(
    SQLXMLParsingMixin,
    SQLXMLSerializationMixin,
    SQLXMLConstructionMixin,
    SQLXMLAggregationMixin,
    SQLXMLQueryingMixin,
):
    """Mixin for complete SQL/XML standard support."""
