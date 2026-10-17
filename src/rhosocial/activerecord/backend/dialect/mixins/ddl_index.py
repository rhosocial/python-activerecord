# src/rhosocial/activerecord/backend/dialect/mixins/ddl_index.py
"""Dialect mixin for index DDL and full-text search support."""
from typing import List, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError
from ...expression.bases import ToSQLProtocol
from ...expression.objects import Index, Table

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import (
        CreateIndexStatement,
        DropIndexStatement,
    )
    from ...expression.statements.ddl_index import (
        CreateFulltextIndexStatement,
        DropFulltextIndexStatement,
    )
    from ...expression.statements.fulltext_match import FulltextMatch


class IndexMixin:
    """Mixin adding support for index DDL statements.

    Also provides full-text index creation and ``MATCH ... AGAINST`` query
    rendering; the DDL and query capabilities are probed independently via
    :meth:`supports_fulltext_index` and :meth:`supports_fulltext_search`.
    """

    def supports_create_index(self) -> bool:
        """Whether CREATE INDEX is supported.

        Defaults to True.
        """
        return True

    def supports_drop_index(self) -> bool:
        """Whether DROP INDEX is supported.

        Defaults to True.
        """
        return True

    def preferred_create_index_statement(self):
        """The backend's preferred CREATE INDEX statement class (§5.12).

        Defaults to ``None`` — the generic ``CreateIndexStatement``.
        """
        return None

    def preferred_drop_index_statement(self):
        """The backend's preferred DROP INDEX statement class (§5.12).

        Defaults to ``None`` — the generic ``DropIndexStatement``.
        """
        return None

    def supports_unique_index(self) -> bool:
        """Whether UNIQUE indexes are supported.

        Defaults to True.
        """
        return True

    def supports_index_if_not_exists(self) -> bool:
        """Whether CREATE INDEX IF NOT EXISTS is supported.

        Defaults to False.
        """
        return False

    def supports_index_if_exists(self) -> bool:
        """Whether DROP INDEX IF EXISTS is supported.

        Defaults to False.
        """
        return False

    def supports_index_type(self) -> bool:
        """Whether index type specification is supported.

        Defaults to False.
        """
        return False

    def supports_partial_index(self) -> bool:
        """Whether partial indexes are supported.

        Defaults to False.
        """
        return False

    def supports_functional_index(self) -> bool:
        """Whether functional indexes are supported.

        Defaults to False.
        """
        return False

    def supports_index_include(self) -> bool:
        """Whether INCLUDE clause is supported.

        Defaults to False.
        """
        return False

    def supports_index_tablespace(self) -> bool:
        """Whether tablespace specification is supported.

        Defaults to False.
        """
        return False

    def supports_drop_index_on_table(self) -> bool:
        """Whether DROP INDEX accepts/requires the ``ON <table>`` clause.

        MySQL/MariaDB/SQL Server use ``DROP INDEX name ON table``;
        PostgreSQL/SQLite/Oracle drop indexes by name without ``ON``.
        When False, the generic ``format_drop_index_statement`` omits the
        ``ON <table>`` suffix even if the expression carries a table name.

        Defaults to True.
        """
        return True

    def supports_concurrent_index(self) -> bool:
        """Whether CREATE INDEX CONCURRENTLY is supported.

        Defaults to False.
        """
        return False

    def get_supported_index_types(self) -> List[str]:
        """Return the list of index types supported by the dialect.

        Returns:
            List of index type names, e.g. ``["BTREE"]``.
        """
        return ["BTREE"]

    def supports_fulltext_index(self) -> bool:
        """Whether MySQL-style ``CREATE FULLTEXT INDEX`` DDL is supported.

        This method reports the ability to issue a DDL statement that
        creates a dedicated fulltext index structure.  It does *not*
        indicate whether the dialect can perform full-text search queries
        — that is the responsibility of :meth:`supports_fulltext_search`.

        For most dialects index creation and query capability go hand in
        hand (MySQL, MariaDB, SQL Server) — creating a FULLTEXT index
        automatically enables ``MATCH ... AGAINST`` queries.  Dialects
        that provide full-text search through a *different* DDL mechanism
        (e.g. PostgreSQL ``GIN`` on ``to_tsvector``, SQLite ``FTS5``
        virtual tables) must override both methods independently.

        Defaults to False.
        """
        return False

    def supports_fulltext_search(self) -> bool:
        """Whether full-text search **querying** is supported.

        Separates query capability from DDL capability reported by
        :meth:`supports_fulltext_index`.  For dialects where the two
        are symmetric the default delegates to ``supports_fulltext_index()``.

        Dialects whose query-side full-text support works through a
        different indexing mechanism (PostgreSQL ``tsvector``/``tsquery``,
        SQLite ``FTS5``) **must** override this method to report their
        actual query capability, which may differ from the DDL-only
        ``supports_fulltext_index()``.
        """
        return self.supports_fulltext_index()

    def supports_fulltext_parser(self) -> bool:
        """Whether FULLTEXT parser plugin (``WITH PARSER``) is supported.

        Defaults to False.
        """
        return False

    def supports_fulltext_boolean_mode(self) -> bool:
        """Whether BOOLEAN MODE is supported.

        Defaults to the result of :meth:`supports_fulltext_index`.
        """
        return self.supports_fulltext_index()

    def supports_fulltext_query_expansion(self) -> bool:
        """Whether QUERY EXPANSION is supported.

        Defaults to the result of :meth:`supports_fulltext_index`.
        """
        return self.supports_fulltext_index()

    def format_fulltext_match(
        self, expr: "FulltextMatch"
    ) -> Tuple[str, tuple]:
        """Format MATCH ... AGAINST expression.

        Args:
            expr: FulltextMatch carrying the target ``columns``,
                ``search_term``, and optional ``mode``.

        Returns:
            Tuple of (SQL string, parameters tuple) for the MATCH expression.

        Raises:
            UnsupportedFeatureError: If the dialect does not support full-text
                indexing.
        """
        if not self.supports_fulltext_index():
            raise UnsupportedFeatureError(self.name, "FULLTEXT search")

        cols_str = ", ".join(self.format_identifier(c) for c in expr.columns)

        ph = self.get_parameter_placeholder()
        if expr.mode:
            mode_upper = expr.mode.upper()
            if mode_upper == "BOOLEAN":
                return f"MATCH({cols_str}) AGAINST({ph} IN BOOLEAN MODE)", (expr.search_term,)
            elif mode_upper in ("QUERY EXPANSION", "WITH QUERY EXPANSION"):
                return f"MATCH({cols_str}) AGAINST({ph} WITH QUERY EXPANSION)", (expr.search_term,)

        # Default: NATURAL LANGUAGE MODE
        return f"MATCH({cols_str}) AGAINST({ph} IN NATURAL LANGUAGE MODE)", (expr.search_term,)

    def format_create_fulltext_index_statement(self, expr: "CreateFulltextIndexStatement") -> Tuple[str, tuple]:
        """Format CREATE FULLTEXT INDEX statement from expression object.

        Args:
            expr: CreateFulltextIndexStatement carrying the index name, table
                name, columns, and optional parser.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            TypeError: ``CreateFulltextIndexStatement.index`` is not an Index.
            Another object kind would have had its own name rendered as the index's.
            TypeError: ``CreateFulltextIndexStatement.table`` is not a Table.
            Another object kind would have had its own name rendered as the table's.
            UnsupportedFeatureError: If the dialect does not support full-text
                indexing.
        """
        if not isinstance(expr.index, Index):
            raise TypeError(
                f"CreateFulltextIndexStatement.index must be an Index, "
                f"got {type(expr.index).__name__}"
            )

        if not isinstance(expr.table, Table):
            raise TypeError(
                f"CreateFulltextIndexStatement.table must be a Table, "
                f"got {type(expr.table).__name__}"
            )
        if not self.supports_fulltext_index():
            raise UnsupportedFeatureError(self.name, "FULLTEXT INDEX")

        parts = ["CREATE FULLTEXT INDEX"]
        if expr.if_not_exists:
            if not self.supports_index_if_not_exists():
                raise UnsupportedFeatureError(
                    self.name, "CREATE INDEX IF NOT EXISTS",
                    f"{self.name} does not support CREATE INDEX IF NOT EXISTS."
                )
            parts.append("IF NOT EXISTS")
        parts.append(expr.index.to_sql()[0])
        parts.append("ON")
        parts.append(expr.table.to_sql()[0])

        cols_str = ", ".join(self.format_identifier(c) for c in expr.columns)
        parts.append(f"({cols_str})")

        if expr.parser:
            if not self.supports_fulltext_parser():
                raise UnsupportedFeatureError(
                    self.name, "FULLTEXT INDEX WITH PARSER",
                    f"{self.name} does not support FULLTEXT INDEX WITH PARSER."
                )
            parts.append(f"WITH PARSER {self.format_identifier(expr.parser)}")

        return " ".join(parts), ()

    def format_drop_fulltext_index_statement(self, expr: "DropFulltextIndexStatement") -> Tuple[str, tuple]:
        """Format DROP FULLTEXT INDEX statement from expression object.

        Args:
            expr: DropFulltextIndexStatement carrying the index name, table
                name, and optional ``if_exists`` flag.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            TypeError: ``DropFulltextIndexStatement.index`` is not an Index.
            Another object kind would have had its own name rendered as the index's.
            TypeError: ``DropFulltextIndexStatement.table`` is not a Table. Another
            object kind would have had its own name rendered as the table's.
            UnsupportedFeatureError: If the dialect does not support full-text
                indexing.
        """
        if not isinstance(expr.index, Index):
            raise TypeError(
                f"DropFulltextIndexStatement.index must be an Index, "
                f"got {type(expr.index).__name__}"
            )

        if not isinstance(expr.table, Table):
            raise TypeError(
                f"DropFulltextIndexStatement.table must be a Table, "
                f"got {type(expr.table).__name__}"
            )
        if not self.supports_fulltext_index():
            raise UnsupportedFeatureError(self.name, "FULLTEXT INDEX")

        parts = ["DROP INDEX"]
        if expr.if_exists:
            if not self.supports_index_if_exists():
                raise UnsupportedFeatureError(
                    self.name, "DROP INDEX IF EXISTS",
                    f"{self.name} does not support DROP INDEX IF EXISTS."
                )
            parts.append("IF EXISTS")
        parts.append(expr.index.to_sql()[0])
        parts.append("ON")
        parts.append(expr.table.to_sql()[0])

        return " ".join(parts), ()

    def format_create_index_statement(self, expr: "CreateIndexStatement") -> Tuple[str, tuple]:
        """Format CREATE INDEX statement per SQL standard.

        Args:
            expr: CreateIndexStatement carrying the index definition,
                including optional unique, index type, include, where, and
                tablespace clauses.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            TypeError: ``CreateIndexStatement.index`` is not an Index. Another
            object kind would have had its own name rendered as the index's.
            TypeError: ``CreateIndexStatement.table`` is not a Table. Another
            object kind would have had its own name rendered as the table's.
            UnsupportedFeatureError: If the dialect does not support
                specific index options.
        """
        if not isinstance(expr.index, Index):
            raise TypeError(
                f"CreateIndexStatement.index must be an Index, "
                f"got {type(expr.index).__name__}"
            )

        if not isinstance(expr.table, Table):
            raise TypeError(
                f"CreateIndexStatement.table must be a Table, "
                f"got {type(expr.table).__name__}"
            )
        from ..exceptions import UnsupportedFeatureError
        all_params = []
        parts = ["CREATE"]

        if expr.unique:
            parts.append("UNIQUE")
        parts.append("INDEX")

        # CONCURRENTLY is a PostgreSQL extension gated by
        # supports_concurrent_index(); it follows the INDEX keyword
        # (``CREATE [UNIQUE] INDEX CONCURRENTLY ...``).
        if expr.concurrent:
            if not self.supports_concurrent_index():
                raise UnsupportedFeatureError(
                    self.name, "CREATE INDEX CONCURRENTLY",
                    f"{self.name} does not support CREATE INDEX CONCURRENTLY."
                )
            parts.append("CONCURRENTLY")

        if expr.if_not_exists:
            if not self.supports_index_if_not_exists():
                raise UnsupportedFeatureError(
                    self.name, "CREATE INDEX IF NOT EXISTS",
                    f"{self.name} does not support CREATE INDEX IF NOT EXISTS."
                )
            parts.append("IF NOT EXISTS")
        parts.append(expr.index.to_sql()[0])
        parts.append("ON")
        parts.append(expr.table.to_sql()[0])

        if expr.index_type:
            if not self.supports_index_type():
                raise UnsupportedFeatureError(
                    self.name, "CREATE INDEX USING <type>",
                    f"{self.name} does not support index type specification.",
                )
            parts.append(f"USING {expr.index_type}")

        col_parts = []
        for col in expr.columns:
            if isinstance(col, ToSQLProtocol):
                col_sql, col_params = col.to_sql()
                col_parts.append(col_sql)
                all_params.extend(col_params)
            else:
                col_parts.append(self.format_identifier(str(col)))
        parts.append(f"({', '.join(col_parts)})")

        if expr.include:
            if not self.supports_index_include():
                raise UnsupportedFeatureError(
                    self.name, "CREATE INDEX INCLUDE",
                    f"{self.name} does not support CREATE INDEX INCLUDE."
                )
            include_cols = ", ".join(self.format_identifier(c) for c in expr.include)
            parts.append(f"INCLUDE ({include_cols})")

        if expr.where:
            if not self.supports_partial_index():
                raise UnsupportedFeatureError(
                    self.name, "CREATE INDEX ... WHERE (partial index)",
                    f"{self.name} does not support partial indexes.",
                )
            # The WHERE of a partial index is a DDL position: the condition
            # renders inline-only (its literals are lifted to the DDL
            # literal class by the condition preparer).
            where_sql = self._format_ddl_condition(expr.where)
            parts.append(f"WHERE {where_sql}")

        if expr.tablespace:
            if not self.supports_index_tablespace():
                raise UnsupportedFeatureError(
                    self.name, "CREATE INDEX TABLESPACE",
                    f"{self.name} does not support CREATE INDEX TABLESPACE."
                )
            parts.append(f"TABLESPACE {self.format_identifier(expr.tablespace)}")

        return " ".join(parts), tuple(all_params)

    def format_drop_index_statement(self, expr: "DropIndexStatement") -> Tuple[str, tuple]:
        """Format DROP INDEX statement per SQL standard.

        Args:
            expr: DropIndexStatement carrying the index name, optional
                ``if_exists`` flag, and optional table name.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            TypeError: ``DropIndexStatement.index`` is not an Index. Another object
            kind would have had its own name rendered as the index's.
            TypeError: ``DropIndexStatement.table`` is not a Table. Another object
            kind would have had its own name rendered as the table's.
            UnsupportedFeatureError: If the dialect does not support
                DROP INDEX IF EXISTS.
        """
        if not isinstance(expr.index, Index):
            raise TypeError(
                f"DropIndexStatement.index must be an Index, "
                f"got {type(expr.index).__name__}"
            )

        if expr.table is not None and not isinstance(expr.table, Table):
            raise TypeError(
                f"DropIndexStatement.table must be a Table, "
                f"got {type(expr.table).__name__}"
            )
        from ..exceptions import UnsupportedFeatureError
        parts = ["DROP INDEX"]
        if expr.concurrent:
            if not self.supports_concurrent_index():
                raise UnsupportedFeatureError(
                    self.name, "DROP INDEX CONCURRENTLY",
                    f"{self.name} does not support DROP INDEX CONCURRENTLY."
                )
            parts.append("CONCURRENTLY")
        if expr.if_exists:
            if not self.supports_index_if_exists():
                raise UnsupportedFeatureError(
                    self.name, "DROP INDEX IF EXISTS",
                    f"{self.name} does not support DROP INDEX IF EXISTS."
                )
            parts.append("IF EXISTS")
        parts.append(expr.index.to_sql()[0])
        if expr.table and self.supports_drop_index_on_table():
            parts.append("ON")
            parts.append(expr.table.to_sql()[0])
        return " ".join(parts), ()
