# src/rhosocial/activerecord/backend/dialect/mixins/ddl_index.py
from typing import List, Optional, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError
from ...expression.bases import ToSQLProtocol

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import (
        CreateIndexExpression,
        DropIndexExpression,
    )
    from ...expression import CreateFulltextIndexExpression, DropFulltextIndexExpression


class IndexMixin:
    """Mixin for index DDL support."""

    def supports_create_index(self) -> bool:
        """Whether CREATE INDEX is supported."""
        return True

    def supports_drop_index(self) -> bool:
        """Whether DROP INDEX is supported."""
        return True

    def supports_unique_index(self) -> bool:
        """Whether UNIQUE indexes are supported."""
        return True

    def supports_index_if_not_exists(self) -> bool:
        """Whether CREATE INDEX IF NOT EXISTS is supported."""
        return False

    def supports_index_if_exists(self) -> bool:
        """Whether DROP INDEX IF EXISTS is supported."""
        return False

    def supports_index_type(self) -> bool:
        """Whether index type specification is supported."""
        return False

    def supports_partial_index(self) -> bool:
        """Whether partial indexes are supported."""
        return False

    def supports_functional_index(self) -> bool:
        """Whether functional indexes are supported."""
        return False

    def supports_index_include(self) -> bool:
        """Whether INCLUDE clause is supported."""
        return False

    def supports_index_tablespace(self) -> bool:
        """Whether tablespace specification is supported."""
        return False

    def supports_concurrent_index(self) -> bool:
        """Whether CREATE INDEX CONCURRENTLY is supported."""
        return False

    def get_supported_index_types(self) -> List[str]:
        """Return list of supported index types."""
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
        """Whether FULLTEXT parser plugin (``WITH PARSER``) is supported."""
        return False

    def supports_fulltext_boolean_mode(self) -> bool:
        """Whether BOOLEAN MODE is supported."""
        return self.supports_fulltext_index()

    def supports_fulltext_query_expansion(self) -> bool:
        """Whether QUERY EXPANSION is supported."""
        return self.supports_fulltext_index()

    def format_fulltext_match(
        self, columns: List[str], search_term: str, mode: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """Format MATCH ... AGAINST expression."""
        if not self.supports_fulltext_index():
            raise UnsupportedFeatureError(self.name, "FULLTEXT search")

        cols_str = ", ".join(self.format_identifier(c) for c in columns)

        ph = self.get_parameter_placeholder()
        if mode:
            mode_upper = mode.upper()
            if mode_upper == "BOOLEAN":
                return f"MATCH({cols_str}) AGAINST({ph} IN BOOLEAN MODE)", (search_term,)
            elif mode_upper in ("QUERY EXPANSION", "WITH QUERY EXPANSION"):
                return f"MATCH({cols_str}) AGAINST({ph} WITH QUERY EXPANSION)", (search_term,)

        # Default: NATURAL LANGUAGE MODE
        return f"MATCH({cols_str}) AGAINST({ph} IN NATURAL LANGUAGE MODE)", (search_term,)

    def format_create_fulltext_index_statement(self, expr: "CreateFulltextIndexExpression") -> Tuple[str, tuple]:
        """Format CREATE FULLTEXT INDEX statement from expression object."""
        if not self.supports_fulltext_index():
            raise UnsupportedFeatureError(self.name, "FULLTEXT INDEX")

        parts = ["CREATE FULLTEXT INDEX"]
        if expr.if_not_exists and self.supports_index_if_not_exists():
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.index_name))
        parts.append("ON")
        parts.append(self.format_identifier(expr.table_name))

        cols_str = ", ".join(self.format_identifier(c) for c in expr.columns)
        parts.append(f"({cols_str})")

        if expr.parser and self.supports_fulltext_parser():
            parts.append(f"WITH PARSER {self.format_identifier(expr.parser)}")

        return " ".join(parts), ()

    def format_drop_fulltext_index_statement(self, expr: "DropFulltextIndexExpression") -> Tuple[str, tuple]:
        """Format DROP FULLTEXT INDEX statement from expression object."""
        if not self.supports_fulltext_index():
            raise UnsupportedFeatureError(self.name, "FULLTEXT INDEX")

        parts = ["DROP INDEX"]
        if expr.if_exists and self.supports_index_if_exists():
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.index_name))
        parts.append("ON")
        parts.append(self.format_identifier(expr.table_name))

        return " ".join(parts), ()

    def format_create_index_statement(self, expr: "CreateIndexExpression") -> Tuple[str, tuple]:
        """Format CREATE INDEX statement per SQL standard."""
        all_params = []
        parts = ["CREATE"]

        if expr.unique:
            parts.append("UNIQUE")
        parts.append("INDEX")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.index_name))
        parts.append("ON")
        parts.append(self.format_identifier(expr.table_name))

        if expr.index_type:
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
            include_cols = ", ".join(self.format_identifier(c) for c in expr.include)
            parts.append(f"INCLUDE ({include_cols})")

        if expr.where:
            where_sql, where_params = expr.where.to_sql()
            parts.append(f"WHERE {where_sql}")
            all_params.extend(where_params)

        if expr.tablespace:
            parts.append(f"TABLESPACE {self.format_identifier(expr.tablespace)}")

        return " ".join(parts), tuple(all_params)

    def format_drop_index_statement(self, expr: "DropIndexExpression") -> Tuple[str, tuple]:
        """Format DROP INDEX statement per SQL standard."""
        parts = ["DROP INDEX"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.index_name))
        if expr.table_name:
            parts.append("ON")
            parts.append(self.format_identifier(expr.table_name))
        return " ".join(parts), ()
