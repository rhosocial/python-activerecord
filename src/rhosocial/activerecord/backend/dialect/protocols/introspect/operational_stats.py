# src/rhosocial/activerecord/backend/dialect/protocols/introspect/operational_stats.py
"""Operational statistics: how the engine says its objects have behaved.

These questions read counters rather than declarations -- how often an index
served a query, how much a table was read and written, what the engine
measured about itself since its last reset -- plus the object dependency
graph, which states what is declared to depend on what.

Every number here is *since something*: the window is part of the answer and
is carried in ``source`` rather than left to a comment. :mod:`...structure`
asks what an object is; :mod:`...data_profile` asks what its rows look like.

The async twin declares the same members in the same order; the ``format_*``
methods stay synchronous because they perform no I/O.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.introspection.introspection import (
        IndexUsageStatsQueryStatement,
        ObjectDependencyQueryStatement,
        RuntimeMetricsQueryStatement,
        TableUsageStatsQueryStatement,
        UnusedIndexesQueryStatement,
    )


@runtime_checkable
class OperationalStatsIntrospectionSupport(Protocol):
    """Protocol for operational statistics capability declaration."""

    # ========== Capability Detection ==========

    def supports_runtime_stats(self) -> bool:
        """Whether the engine's live runtime measurements are answerable.

        Answering ``True`` obliges
        :meth:`format_runtime_metrics_query_statement` to render. What the
        numbers cover is the backend's to state: every one of them is *since
        something* -- a statistics reset, a server start, a DMV flush -- and
        the window is where the meaning lives. See
        :class:`RuntimeMetricItem` for why ``source`` is part of the answer
        rather than a comment.
        """
        ...  # pragma: no cover

    def supports_index_stats(self) -> bool:
        """Whether per-index use counters are answerable.

        A different question from ``supports_unused_indexes_detection``:
        that one asks "has this index ever been used", this one asks "how
        much is it used". Both are worth asking of an index and they have
        different costs and different answers, so they stay separate rather
        than becoming one type with a flag.
        """
        ...  # pragma: no cover

    def supports_table_stats(self) -> bool:
        """Whether per-table usage counters are answerable.

        Answering ``True`` obliges
        :meth:`format_table_usage_stats_query_statement` to render, and the
        rendered query to return at least the address columns plus the
        read/write counter set that has a name in
        ``TableUsageStats``. Every counter is *since the statistics were last
        reset*, on whatever schedule the engine resets them -- that part is
        the backend's to document, not the protocol's to guess.
        """
        ...  # pragma: no cover

    def supports_unused_indexes_detection(self) -> bool:
        """Whether unused indexes detection is supported.

        Answering ``True`` means :meth:`format_unused_indexes_query_statement`
        renders for this dialect. What "unused" *means* is the backend's to
        state -- counters reset, views cover only the statistics they can see,
        and an index missing from the answer is absence of evidence, never
        proof of use. The common minimum returned is an address; the engine's
        own numbers ride on its subclass or in ``extra``.
        """
        ...  # pragma: no cover

    def supports_object_dependencies(self) -> bool:
        """Whether the object dependency graph is answerable.

        The graph is *declared*, not inferred: an engine reports what its
        catalog records as depending on what, and ``kind`` / ``action`` carry
        the relation and the drop behaviour in the engine's own vocabulary.
        """
        ...  # pragma: no cover

    # ========== Query Formatting ==========

    def format_unused_indexes_query_statement(
        self, expr: "UnusedIndexesQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format an unused-indexes listing.

        The one place the family's meaning is fixed: whatever an engine
        counts, the rendered query must return at least the three address
        columns -- schema, table, index -- because the caller receives
        ``UnusedIndexInfo`` and nothing downstream can rebuild an address out
        of a statistic. What the numbers *mean* is the backend's to state.

        Args:
            expr: Unused indexes expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_table_usage_stats_query_statement(
        self, expr: "TableUsageStatsQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a per-table usage-counter listing.

        The contract the family fixes: the rendered query returns at least
        the address columns plus whatever subset of the common counters the
        engine tracks -- a counter the engine does not keep is left out of
        the projection rather than rendered as a zero it never measured.

        Args:
            expr: Table usage stats expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_runtime_metrics_query_statement(
        self, expr: "RuntimeMetricsQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a runtime-measurement listing.

        The contract: each row carries a name and a value, and the answer as a
        whole states its window in ``source`` -- the engine's reset schedule is
        what makes a zero mean "nothing happened" rather than "nothing ever
        happened".

        Args:
            expr: Runtime metrics expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_index_usage_stats_query_statement(
        self, expr: "IndexUsageStatsQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a per-index use-counter listing.

        The contract: the address columns plus the counters the engine keeps.
        A counter the engine does not keep is left out of the projection
        rather than rendered as a zero it never measured.

        Args:
            expr: Index usage stats expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_object_dependency_query_statement(
        self, expr: "ObjectDependencyQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format an object-dependency listing.

        The contract: the dependent object, the referenced object, and the
        relation between them in the engine's vocabulary. Direction matters
        and is fixed here -- ``dependent`` needs ``referenced`` -- because a
        reader asking "what breaks if I drop this" is asking about dependants,
        not about dependencies.

        Args:
            expr: Object dependency expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover


@runtime_checkable
class AsyncOperationalStatsIntrospectionSupport(Protocol):
    """Async twin of :class:`OperationalStatsIntrospectionSupport`."""

    def supports_runtime_stats(self) -> bool:
        ...  # pragma: no cover

    def supports_index_stats(self) -> bool:
        ...  # pragma: no cover

    def supports_table_stats(self) -> bool:
        ...  # pragma: no cover

    def supports_unused_indexes_detection(self) -> bool:
        ...  # pragma: no cover

    def supports_object_dependencies(self) -> bool:
        ...  # pragma: no cover

    def format_unused_indexes_query_statement(
        self, expr: "UnusedIndexesQueryStatement"
    ) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_table_usage_stats_query_statement(
        self, expr: "TableUsageStatsQueryStatement"
    ) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_runtime_metrics_query_statement(
        self, expr: "RuntimeMetricsQueryStatement"
    ) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_index_usage_stats_query_statement(
        self, expr: "IndexUsageStatsQueryStatement"
    ) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_object_dependency_query_statement(
        self, expr: "ObjectDependencyQueryStatement"
    ) -> Tuple[str, tuple]:
        ...  # pragma: no cover
