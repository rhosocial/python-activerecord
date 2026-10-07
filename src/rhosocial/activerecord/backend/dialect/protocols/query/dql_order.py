# src/rhosocial/activerecord/backend/dialect/protocols/query/dql_order.py
"""Ordering and row-limiting a SELECT produces.

Whether ORDER BY accepts NULLS FIRST / NULLS LAST, whether FETCH WITH TIES
is spelled out, and whether OFFSET may appear without LIMIT are three
different questions an engine answers separately -- MySQL rejects the last
one, and no engine changes its mind about the first two on their account.
"""

from typing import Protocol, runtime_checkable

@runtime_checkable
class DqlOrderSupport(Protocol):
    """Ordering and row-limiting switches."""

    def supports_nulls_first_last(self) -> bool:
        """Whether the engine accepts the form ``nulls_first_last``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def supports_fetch_with_ties(self) -> bool:
        """Whether the engine accepts the form ``fetch_with_ties``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def supports_offset_without_limit(self) -> bool:
        """Whether the engine accepts the form ``offset_without_limit``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover
