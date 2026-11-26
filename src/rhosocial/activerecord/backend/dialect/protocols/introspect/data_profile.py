# src/rhosocial/activerecord/backend/dialect/protocols/introspect/data_profile.py
"""Data profiling: what the rows in a column actually look like.

Structure introspection reads what a column is *declared* to be; these
questions read what is stored in it -- null fraction, distinct count,
endpoints, most frequent values, and whether two columns' value domains
overlap. The first answers from a statistics catalogue on some engines and
from an aggregate scan on others, which is why the answer carries its
provenance: an estimate and an exact count are different facts.

The async twin declares the same members in the same order; the ``format_*``
methods stay synchronous because they perform no I/O.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.introspection import (
        ColumnDataProfileQueryStatement,
        ColumnValueSampleQueryStatement,
        JoinCoverageQueryStatement,
    )


@runtime_checkable
class DataProfileIntrospectionSupport(Protocol):
    """Protocol for column data profiling capability declaration."""

    # ========== Capability Detection ==========

    def supports_column_data_profile(self) -> bool:
        """Whether a column's *data* can be profiled, not just its declaration.

        Answering ``True`` obliges
        :meth:`format_column_data_profile_query_statement`. The answer must
        carry, at least, the column address and whichever of the five core
        figures the engine actually measures -- null fraction, distinct count,
        minimum, maximum, row count -- plus the provenance in
        ``ColumnDataProfile.source``, because an estimate and an exact count
        are not the same fact.
        """
        ...  # pragma: no cover

    def supports_column_value_sample(self) -> bool:
        """Whether a column's most frequent values are answerable.

        Separate from :meth:`supports_column_data_profile` because the costs
        differ by orders of magnitude on every engine: a statistics catalogue
        answers the profile for free, while a value listing either comes from
        a kept ``most_common_vals`` list or has to aggregate. One probe for
        both would price the cheap question at the expensive answer.
        """
        ...  # pragma: no cover

    def supports_join_coverage(self) -> bool:
        """Whether two columns' value domains can be compared for overlap.

        The most expensive probe in this protocol, and the only one about a
        *relation* rather than an object. Answering ``True`` obliges
        :meth:`format_join_coverage_query_statement`; the result is always an
        estimate -- nulls are excluded, collations are not reconciled, and a
        sample may have been used -- which is why both fractions are reported
        rather than one similarity score.
        """
        ...  # pragma: no cover

    # ========== Query Formatting ==========

    def format_column_data_profile_query_statement(
        self, expr: "ColumnDataProfileQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a per-column data profile for one table.

        The contract: one row per column, carrying the column address and the
        figures the engine measures, with the projection *omitting* a figure
        the engine does not keep rather than rendering a constant. Provenance
        (estimate versus aggregate) is the backend's to attach, and it is part
        of the answer rather than a comment on it.

        Args:
            expr: Column data profile expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_column_value_sample_query_statement(
        self, expr: "ColumnValueSampleQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a most-frequent-values listing for one column.

        The contract: the value and at least one of count or frequency. Both
        are exposed by ``ColumnValueFrequency`` because engines differ, and a
        backend that has one must not fabricate the other.

        Args:
            expr: Column value sample expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_join_coverage_query_statement(
        self, expr: "JoinCoverageQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a two-sided value-domain overlap measurement.

        The contract: a row carrying the left and right coverage fractions,
        each in ``[0.0, 1.0]``, over *distinct* values -- a coverage over rows
        rather than values would make a heavily repeated key look well
        covered by one match.

        Args:
            expr: Join coverage expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover


@runtime_checkable
class AsyncDataProfileIntrospectionSupport(Protocol):
    """Async twin of :class:`DataProfileIntrospectionSupport`."""

    def supports_column_data_profile(self) -> bool:
        ...  # pragma: no cover

    def supports_column_value_sample(self) -> bool:
        ...  # pragma: no cover

    def supports_join_coverage(self) -> bool:
        ...  # pragma: no cover

    def format_column_data_profile_query_statement(
        self, expr: "ColumnDataProfileQueryStatement"
    ) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_column_value_sample_query_statement(
        self, expr: "ColumnValueSampleQueryStatement"
    ) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_join_coverage_query_statement(
        self, expr: "JoinCoverageQueryStatement"
    ) -> Tuple[str, tuple]:
        ...  # pragma: no cover
