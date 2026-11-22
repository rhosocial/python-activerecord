# src/rhosocial/activerecord/backend/dialect/mixins/fulltext_index_mixin.py
"""Per-statement mixin for FulltextIndexSupport. Members/order/signature mirror the protocol."""

from typing import List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.bases import ToSQLProtocol
from rhosocial.activerecord.backend.expression.objects import Index, Table

class FulltextIndexMixin:
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
