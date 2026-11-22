# .../mixins/dql_order_mixin.py
"""Per-feature mixin for DqlOrderSupport. Members/order/signature mirror the protocol."""

from typing import TYPE_CHECKING, Any, List, Tuple
from ...expression.bases import ToSQLProtocol
from ...expression.query_parts import SortDirection

class DqlOrderMixin:
    def supports_nulls_first_last(self) -> bool:
            """Whether ``ORDER BY ... NULLS FIRST`` / ``NULLS LAST`` is supported.

            Defaults to False; dialects that accept explicit null ordering
            (PostgreSQL, Oracle, Snowflake, Firebird, ...) override to True.
            """
            return False

    def supports_fetch_with_ties(self) -> bool:
            """Whether ``FETCH FIRST n ROWS WITH TIES`` is supported.

            The default mirrors PostgreSQL's version gate (13+). Every other
            backend overrides this with its own real capability.
            """
            return self.version_at_least((13, 0, 0))

    def supports_offset_without_limit(self) -> bool:
            """Whether OFFSET may appear without LIMIT (defaults to False)."""
            return False
