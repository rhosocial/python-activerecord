# src/rhosocial/activerecord/backend/dialect/mixins/relation_source.py
"""
The ``FROM`` side of a statement: every row source a query can be built from.

:class:`~rhosocial.activerecord.backend.expression.sources.NamedRelationRef`
points a query at a relation and adds what the query needs and the object does
not have: an alias, and the engine-specific time-travel clause Snowflake spells
``AT`` / ``BEFORE``.

The name itself is not rendered here. ``ref.relation.to_sql()`` goes through the
relation's own ``format_table_object``, so a table, a view and a materialized
view are named by their own protocols and this method never needs to know which
kind it got. That is the separation the old ``NamedRelationRef`` lacked: it
rendered the name, the alias and the temporal clause from one class, which is
why an index could be spelled with a table expression.

The remaining row sources -- a derived table, a ``VALUES`` list, a table
function, ``GRAPH_TABLE``, ``JSON_TABLE``, ``XMLTABLE`` -- have no catalogue
identity at all, so there is nothing for a name protocol to render. Each one is
rendered here against generic SQL, and each one first asks whether this dialect
supports it at all: a derived table is universal SQL, whereas ``VALUES`` in a
``FROM`` clause, a table function, and the three SQL/XML-and-projection forms
are engine-specific and default to unsupported.
"""

from typing import Any, List, Tuple, TYPE_CHECKING

from ...expression.bases import BaseExpression
from ...expression.objects import RelationObject

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.sources import (
        DerivedTableSource,
        GraphTableSource,
        JsonTableSource,
        NamedRelationRef,
        TableFunctionSource,
        TableSource,
        ValuesTableSource,
        XmlTableSource,
    )

__all__ = ["RelationSourceMixin"]


class RelationSourceMixin:
    """Renders a ``FROM`` clause reference to any kind of row source."""

    def supports_derived_table(self) -> bool:
        """Whether a parenthesised subquery is usable as a row source.

        Universal in SQL, so this defaults to True. A dialect overrides it only
        if its engines genuinely reject a subquery in ``FROM``.
        """
        return True

    def supports_values_table_constructor(self) -> bool:
        """Whether a literal row constructor is usable as a row source.

        Not universal -- SQL Server has no ``VALUES`` table source -- so this
        defaults to False and a dialect opts in. Named for the SQL standard's
        ``table value constructor``, which is the name MySQL and ClickHouse
        already give this capability in their own probes.
        """
        return False

    def supports_table_function(self) -> bool:
        """Whether a function called for its rows is usable as a row source.

        Engines spell this differently enough that the spelling is the
        dialect's, but the capability is common, so it defaults to False and a
        dialect opts in.
        """
        return False

    def format_named_relation(self, ref: "NamedRelationRef") -> Tuple[str, tuple]:
        """Render a :class:`~...expression.sources.NamedRelationRef`.

        The relation's name comes from the relation itself; the temporal clause
        and the alias are the query's, and are the dialect's to spell.

        Args:
            ref: The reference being rendered.

        Returns:
            A ``(sql, params)`` tuple. ``params`` carries the temporal clause's
            parameters when there is one; a plain name binds nothing.

        Raises:
            TypeError: ``NamedRelationRef.relation`` is not a RelationObject. An
            index or a sequence cannot be read from, yet either would still have
            rendered its own name into the FROM clause.
        """
        if not isinstance(ref.relation, RelationObject):
            raise TypeError(
                f"NamedRelationRef.relation must be a RelationObject, "
                f"got {type(ref.relation).__name__}"
            )
        name_sql, params = ref.relation.to_sql()

        if ref.temporal_options:
            from ...expression.datetime import TemporalOptionsExpression

            temporal = self.format_temporal_options(
                TemporalOptionsExpression(self, ref.temporal_options)
            )
            if temporal is not None:
                temporal_sql, temporal_params = temporal
                name_sql = f"{name_sql} {temporal_sql}"
                params += temporal_params

        if ref.alias:
            name_sql = (
                f"{name_sql}{self.source_alias_separator()}"
                f"{self.format_identifier(ref.alias, ref.alias_need_quote)}"
            )

        return name_sql, params

    def source_alias_separator(self) -> str:
        """The token this dialect places before a row source's alias.

        Engines disagree about whether ``AS`` is written before a table alias, so
        the answer belongs here rather than on the source.
        """
        return " AS "

    def format_source_alias(self, sql: str, source: "TableSource") -> str:
        """Append *source*'s alias to already-rendered *sql*.

        Every row source carries an alias but none of them may decide how it is
        spelled: the separator before it and the quoting of the name are the
        dialect's answers, so each renderer hands its finished fragment here
        rather than repeating those two decisions.

        Args:
            sql: The rendered row source, without its alias.
            source: The source whose alias should be appended.

        Returns:
            *sql* unchanged when the source has no alias, otherwise *sql*
            followed by this dialect's separator and the quoted alias.
        """
        if source.alias is None:
            return sql
        return (
            f"{sql}{self.source_alias_separator()}"
            f"{self.format_identifier(source.alias, source.alias_need_quote)}"
        )

    def format_source_document(self, document: Any) -> Tuple[str, tuple]:
        """Render the document a projection row source reads.

        ``JSON_TABLE`` and ``XMLTABLE`` are handed either an expression
        producing the document or the name of a column holding it, so this
        resolves the two forms in one place rather than in each renderer.

        Args:
            document: A :class:`~...expression.bases.BaseExpression`, or the
                name of a column holding the document.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            TypeError: *document* is neither an expression nor a column name.
        """
        if isinstance(document, BaseExpression):
            return document.to_sql()
        if isinstance(document, str):
            return self.format_identifier(document), ()
        raise TypeError(
            f"A row source's document must be a BaseExpression or a column "
            f"name, got {type(document).__name__}"
        )

    def format_derived_table(self, source: "DerivedTableSource") -> Tuple[str, tuple]:
        """Render a :class:`~...expression.sources.DerivedTableSource`.

        Args:
            source: The derived table, exposing ``query`` and an optional alias.

        Returns:
            A ``(sql, params)`` tuple: the query parenthesised so it reads as a
            row source, followed by the alias when there is one.

        Raises:
            UnsupportedFeatureError: If this dialect rejects subqueries in FROM.
        """
        self.check_feature_support(
            "supports_derived_table", "derived table in FROM"
        )
        query_sql, params = source.query.to_sql()
        return self.format_source_alias(f"({query_sql})", source), params

    def format_values_table(self, source: "ValuesTableSource") -> Tuple[str, tuple]:
        """Render a :class:`~...expression.sources.ValuesTableSource`.

        Each cell is either an expression, which is rendered in place, or a
        plain value, which becomes a bind parameter -- so a literal never binds
        itself as a parameter object.

        Args:
            source: The row constructor, exposing ``rows``, optional
                ``column_names`` and an optional alias.

        Returns:
            A ``(sql, params)`` tuple. ``params`` carries the bound cells; the
            column names, being identifiers, bind nothing.

        Raises:
            UnsupportedFeatureError: If this dialect has no VALUES row source.
        """
        self.check_feature_support(
            "supports_values_table_constructor", "VALUES row source"
        )
        placeholder = self.get_parameter_placeholder()
        all_params: List[Any] = []
        rows_sql = []
        for row in source.rows:
            cells_sql = []
            for cell in row:
                if isinstance(cell, BaseExpression):
                    cell_sql, cell_params = cell.to_sql()
                    all_params.extend(cell_params)
                    cells_sql.append(cell_sql)
                else:
                    all_params.append(cell)
                    cells_sql.append(placeholder)
            rows_sql.append(f"({', '.join(cells_sql)})")
        sql = f"(VALUES {', '.join(rows_sql)})"
        if source.column_names:
            names = ", ".join(
                self.format_identifier(name) for name in source.column_names
            )
            sql = f"{sql} ({names})"
        return self.format_source_alias(sql, source), tuple(all_params)

    def format_table_function(self, source: "TableFunctionSource") -> Tuple[str, tuple]:
        """Render a :class:`~...expression.sources.TableFunctionSource`.

        Args:
            source: The call, exposing ``function_name``, optional ``args``,
                ``with_ordinality`` and an optional alias.

        Returns:
            A ``(sql, params)`` tuple carrying the arguments' parameters. The
            function name is an identifier, so it is rendered unquoted.

        Raises:
            UnsupportedFeatureError: If this dialect cannot call a function for
                its rows.
        """
        self.check_feature_support("supports_table_function", "table function")
        args_sql = []
        all_params: List[Any] = []
        for argument in source.args or ():
            argument_sql, argument_params = argument.to_sql()
            args_sql.append(argument_sql)
            all_params.extend(argument_params)
        name = self.format_identifier(source.function_name, need_quote=False)
        sql = f"{name}({', '.join(args_sql)})"
        if source.with_ordinality:
            sql = f"{sql} WITH ORDINALITY"
        return self.format_source_alias(sql, source), tuple(all_params)

    def format_graph_table(self, source: "GraphTableSource") -> Tuple[str, tuple]:
        """Render a :class:`~...expression.sources.GraphTableSource`.

        Args:
            source: The graph traversal, exposing ``query``, an optional
                ``columns_clause`` and an optional alias.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            UnsupportedFeatureError: If this dialect has no GRAPH_TABLE.
        """
        self.check_feature_support("supports_graph_table", "GRAPH_TABLE")
        query_sql, params = source.query.to_sql()
        sql = f"GRAPH_TABLE({query_sql}"
        if source.columns_clause is not None:
            columns_sql, columns_params = source.columns_clause.to_sql()
            sql = f"{sql} {columns_sql}"
            params += columns_params
        return self.format_source_alias(f"{sql})", source), params

    def format_json_table(self, source: "JsonTableSource") -> Tuple[str, tuple]:
        """Render a :class:`~...expression.sources.JsonTableSource`.

        Args:
            source: The projection, exposing ``source`` (the document),
                ``path`` (the JSON path), ``columns`` and an optional alias.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            UnsupportedFeatureError: If this dialect has no JSON_TABLE.
            TypeError: A column entry declares neither a name nor a path.
        """
        self.check_feature_support("supports_json_table", "JSON_TABLE")
        document_sql, params = self.format_source_document(source.source)
        path = self._escape_sql_string(source.path)
        columns_sql, columns_params = self.format_source_columns(
            source.columns, self.format_json_table_column
        )
        params += columns_params
        sql = f"JSON_TABLE({document_sql}, '{path}' COLUMNS({columns_sql}))"
        return self.format_source_alias(sql, source), params

    def format_source_columns(self, columns: Any, render_column: Any) -> Tuple[str, tuple]:
        """Render a projection source's whole ``COLUMNS`` list.

        ``JSON_TABLE`` and ``XMLTABLE`` both take a list of column projections
        and both spell their entries differently, so only the joining and the
        parameter accumulation are shared.

        Args:
            columns: The column projections, in order.
            render_column: Callable rendering one entry to a
                ``(sql, params)`` tuple.

        Returns:
            A ``(sql, params)`` tuple: the comma-joined entries and the
            parameters every entry contributed, in order.
        """
        entries_sql = []
        all_params: List[Any] = []
        for column in columns:
            entry_sql, entry_params = render_column(column)
            entries_sql.append(entry_sql)
            all_params.extend(entry_params)
        return ", ".join(entries_sql), tuple(all_params)

    def format_json_table_column(self, column: Any) -> Tuple[str, tuple]:
        """Render one entry of a JSON_TABLE ``COLUMNS`` list.

        Args:
            column: An entry exposing ``name``, ``path`` and ``data_type``.

        Returns:
            A ``(sql, params)`` tuple for the ``name type PATH 'path'``
            fragment; a JSON path is a literal, so it binds nothing and only the
            declared type can contribute a parameter.

        Raises:
            TypeError: *column* is not a usable column projection.
        """
        name = getattr(column, "name", None)
        path = getattr(column, "path", None)
        if name is None or path is None:
            raise TypeError(
                f"A JSON_TABLE column must expose a name and a path, "
                f"got {type(column).__name__}"
            )
        type_sql, params = self.format_source_column_type(column)
        escaped_path = self._escape_sql_string(path)
        sql = (
            f"{self.format_identifier(name)} {type_sql} PATH '{escaped_path}'"
        )
        return sql, params

    def format_source_column_type(self, column: Any) -> Tuple[str, tuple]:
        """Render the declared result type of a projection column.

        A column's type is a clause of its own, so an expression type is asked
        to render and a plain one is taken as written.

        Args:
            column: A column projection exposing ``data_type``.

        Returns:
            A ``(sql, params)`` tuple; a type written as plain text binds
            nothing, while an expression type carries its own parameters.

        Raises:
            TypeError: *column* declares no usable ``data_type``.
        """
        data_type = getattr(column, "data_type", None)
        if data_type is None:
            raise TypeError(
                f"A projection column must expose a data_type, "
                f"got {type(column).__name__}"
            )
        if isinstance(data_type, BaseExpression):
            return data_type.to_sql()
        return str(data_type), ()

    def format_xml_table(self, source: "XmlTableSource") -> Tuple[str, tuple]:
        """Render a :class:`~...expression.sources.XmlTableSource`.

        SQL/XML XMLTABLE takes the context item, any ``PASSING`` bindings, the
        row pattern, and the column list, in that order.

        Args:
            source: The projection, exposing ``source`` (the document, or
                ``None`` when ``passing`` supplies it), ``row_path`` (the
                XPath), ``columns``, optional ``passing`` and an optional
                alias.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            UnsupportedFeatureError: If this dialect has no XMLTABLE.
            TypeError: No document is reachable -- neither ``source`` nor
                ``passing`` supplies one.
        """
        self.check_feature_support("supports_xmltable", "XMLTABLE")
        parts: List[str] = []
        all_params: List[Any] = []
        if source.source is not None:
            document_sql, document_params = self.format_source_document(source.source)
            parts.append(document_sql)
            all_params.extend(document_params)
        elif not source.passing:
            raise TypeError(
                "XmlTableSource needs a document: pass `source`, or a "
                "`passing` binding that supplies one."
            )
        for binding in source.passing or ():
            binding_sql, binding_params = self.format_source_document(binding)
            parts.append(f"PASSING {binding_sql}")
            all_params.extend(binding_params)
        row_path = self._escape_sql_string(source.row_path)
        parts.append(f"PASSING '{row_path}'")
        columns_sql, columns_params = self.format_source_columns(
            source.columns, self.format_xml_table_column
        )
        all_params.extend(columns_params)
        parts.append(f"COLUMNS({columns_sql})")
        sql = f"XMLTABLE({' '.join(parts)})"
        return self.format_source_alias(sql, source), tuple(all_params)

    def format_xml_table_column(self, column: Any) -> Tuple[str, tuple]:
        """Render one entry of an XMLTABLE ``COLUMNS`` list.

        Args:
            column: An entry exposing ``name`` and ``data_type``, and
                optionally ``path``, ``default`` and ``for_ordinality``.

        Returns:
            A ``(sql, params)`` tuple for this entry's fragment. Unlike a JSON
            path, an XML column's ``PATH`` and ``DEFAULT`` are clauses that may
            bind, so their parameters are carried up.

        Raises:
            TypeError: *column* exposes no usable ``name``.
        """
        name = getattr(column, "name", None)
        if name is None:
            raise TypeError(
                f"An XMLTABLE column must expose a name, "
                f"got {type(column).__name__}"
            )
        type_sql, all_params = self.format_source_column_type(column)
        fragment = f"{self.format_identifier(name)} {type_sql}"
        for attribute in ("path", "default"):
            value = getattr(column, attribute, None)
            if value is None:
                continue
            value_sql, value_params = self.format_source_document(value)
            fragment = f"{fragment} {attribute.upper()} {value_sql}"
            all_params += value_params
        if getattr(column, "for_ordinality", False):
            fragment = f"{fragment} FOR ORDINALITY"
        return fragment, all_params