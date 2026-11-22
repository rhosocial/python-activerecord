# src/rhosocial/activerecord/backend/dialect/mixins/create_index_mixin.py
"""Per-statement mixin for CreateIndexSupport. Members/order/signature mirror the protocol."""

from typing import List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.bases import ToSQLProtocol
from rhosocial.activerecord.backend.expression.objects import Index, Table

class CreateIndexMixin:
    def supports_create_index(self) -> bool:
            """Whether CREATE INDEX is supported.

            Defaults to True.
            """
            return True

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

    def supports_concurrent_index(self) -> bool:
            """Whether CREATE INDEX CONCURRENTLY is supported.

            Defaults to False.
            """
            return False

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
                where_sql, where_params = expr.where.to_sql()
                parts.append(f"WHERE {where_sql}")
                all_params.extend(where_params)

            if expr.tablespace:
                if not self.supports_index_tablespace():
                    raise UnsupportedFeatureError(
                        self.name, "CREATE INDEX TABLESPACE",
                        f"{self.name} does not support CREATE INDEX TABLESPACE."
                    )
                parts.append(f"TABLESPACE {self.format_identifier(expr.tablespace)}")

            return " ".join(parts), tuple(all_params)

