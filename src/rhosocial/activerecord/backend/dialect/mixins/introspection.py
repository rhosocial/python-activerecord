# src/rhosocial/activerecord/backend/dialect/mixins/introspection.py
"""Dialect mixins for database introspection capability declaration.

The introspection surface is split into four families, each a same-stem pair
with its protocol in :mod:`...protocols.introspect`:

* :class:`StructureIntrospectionMixin` -- what the catalogue declares
  (:mod:`...protocols.introspect.structure`);
* :class:`OperationalStatsIntrospectionMixin` -- how objects have behaved
  (:mod:`...protocols.introspect.operational_stats`);
* :class:`DataProfileIntrospectionMixin` -- what the rows look like
  (:mod:`...protocols.introspect.data_profile`);
* :class:`DdlExtractionIntrospectionMixin` -- the text that recreates an object
  (:mod:`...protocols.introspect.ddl_extraction`).

:class:`IntrospectionMixin` and :class:`AsyncIntrospectionMixin` are
composition-only aggregates of the four: they declare no members of their own,
so a dialect that composes one keeps every family's answer and every
method-name override. The async families declare the ``format_*`` methods
synchronously for the same reason: formatting SQL performs no I/O.

Dialects declare capabilities (``supports_*``) and format the corresponding
metadata queries; query execution and result parsing live in the backend layer.
"""
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.introspection.introspection import (
        ColumnDataProfileQueryStatement,
        ColumnInfoQueryStatement,
        ColumnValueSampleQueryStatement,
        DatabaseInfoQueryStatement,
        DDLStatementQueryStatement,
        ForeignKeyQueryStatement,
        IndexInfoQueryStatement,
        IndexUsageStatsQueryStatement,
        JoinCoverageQueryStatement,
        ObjectDependencyQueryStatement,
        RuntimeMetricsQueryStatement,
        TableInfoQueryStatement,
        TableListQueryStatement,
        TableUsageStatsQueryStatement,
        TriggerInfoQueryStatement,
        TriggerListQueryStatement,
        UnusedIndexesQueryStatement,
        ViewInfoQueryStatement,
        ViewListQueryStatement,
    )


class StructureIntrospectionMixin:
    """
    Mixin for structure introspection capability declaration.

    Dialects declare capabilities (supports_* methods) and provide format_*
    methods to generate database-specific SQL for object-structure queries.
    The actual introspection implementation (query execution and result
    parsing) is in the backend layer via IntrospectionMixin from
    backend.introspection.mixins.

    This base implementation returns False for all supports_* methods,
    indicating structure introspection is not supported by default. The
    format_* methods raise UnsupportedFeatureError when called.
    """

    # ========== Capability Detection ==========

    def supports_introspection(self) -> bool:
        """Whether introspection is supported. Defaults to False."""
        return False

    def supports_database_info(self) -> bool:
        """Whether database information query is supported. Defaults to False."""
        return False

    def supports_table_introspection(self) -> bool:
        """Whether table introspection is supported. Defaults to False."""
        return False

    def supports_column_introspection(self) -> bool:
        """Whether column introspection is supported. Defaults to False."""
        return False

    def supports_index_introspection(self) -> bool:
        """Whether index introspection is supported. Defaults to False."""
        return False

    def supports_foreign_key_introspection(self) -> bool:
        """Whether foreign key introspection is supported. Defaults to False."""
        return False

    def supports_view_introspection(self) -> bool:
        """Whether view introspection is supported. Defaults to False."""
        return False

    def supports_trigger_introspection(self) -> bool:
        """Whether trigger introspection is supported. Defaults to False."""
        return False

    def supports_extensions(self) -> bool:
        """Whether this engine exposes a catalogue of installed add-on components.

        Defaults to ``False``. ``extension`` is not SQL-standard vocabulary and
        the concept differs per engine -- PostgreSQL's are ``CREATE EXTENSION``
        packages with a version and a schema, SQLite's are registered virtual
        table modules -- so a ``True`` promises that the engine *will answer*,
        not *what shape the answer takes*. Read the backend's own docs and
        result type before relying on any field; see
        :class:`~...protocols.introspect.structure.StructureIntrospectionSupport`
        for why the name stays in core despite that.
        """
        return False

    def supports_table_storage_introspection(self) -> bool:
        """Whether per-table storage metrics introspection is supported. Defaults to False."""
        return False

    # ========== Query Formatting ==========

    def format_database_info_query_statement(self, expr: "DatabaseInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format database information query.

        Args:
            expr: Database info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If database info query is not supported.
        """
        if not self.supports_database_info():
            raise UnsupportedFeatureError(self.name, "database info query")
        raise NotImplementedError("Subclass must implement format_database_info_query_statement")

    def format_table_list_query_statement(self, expr: "TableListQueryStatement") -> Tuple[str, tuple]:
        """
        Format table list query.

        Args:
            expr: Table list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If table introspection is not supported.
        """
        if not self.supports_table_introspection():
            raise UnsupportedFeatureError(self.name, "table introspection")
        raise NotImplementedError("Subclass must implement format_table_list_query_statement")

    def format_table_info_query_statement(self, expr: "TableInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format single table information query.

        Args:
            expr: Table info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If table introspection is not supported.
        """
        if not self.supports_table_introspection():
            raise UnsupportedFeatureError(self.name, "table introspection")
        raise NotImplementedError("Subclass must implement format_table_info_query_statement")

    def format_column_info_query_statement(self, expr: "ColumnInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format column information query.

        Args:
            expr: Column info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If column introspection is not supported.
        """
        if not self.supports_column_introspection():
            raise UnsupportedFeatureError(self.name, "column introspection")
        raise NotImplementedError("Subclass must implement format_column_info_query_statement")

    def format_index_info_query_statement(self, expr: "IndexInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format index information query.

        Args:
            expr: Index info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If index introspection is not supported.
        """
        if not self.supports_index_introspection():
            raise UnsupportedFeatureError(self.name, "index introspection")
        raise NotImplementedError("Subclass must implement format_index_info_query_statement")

    def format_foreign_key_query_statement(self, expr: "ForeignKeyQueryStatement") -> Tuple[str, tuple]:
        """
        Format foreign key information query.

        Args:
            expr: Foreign key expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If foreign key introspection is not supported.
        """
        if not self.supports_foreign_key_introspection():
            raise UnsupportedFeatureError(self.name, "foreign key introspection")
        raise NotImplementedError("Subclass must implement format_foreign_key_query_statement")

    def format_view_list_query_statement(self, expr: "ViewListQueryStatement") -> Tuple[str, tuple]:
        """
        Format view list query.

        Args:
            expr: View list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If view introspection is not supported.
        """
        if not self.supports_view_introspection():
            raise UnsupportedFeatureError(self.name, "view introspection")
        raise NotImplementedError("Subclass must implement format_view_list_query_statement")

    def format_view_info_query_statement(self, expr: "ViewInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format single view information query.

        Args:
            expr: View info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If view introspection is not supported.
        """
        if not self.supports_view_introspection():
            raise UnsupportedFeatureError(self.name, "view introspection")
        raise NotImplementedError("Subclass must implement format_view_info_query_statement")

    def format_trigger_list_query_statement(self, expr: "TriggerListQueryStatement") -> Tuple[str, tuple]:
        """
        Format trigger list query.

        Args:
            expr: Trigger list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If trigger introspection is not supported.
        """
        if not self.supports_trigger_introspection():
            raise UnsupportedFeatureError(self.name, "trigger introspection")
        raise NotImplementedError("Subclass must implement format_trigger_list_query_statement")

    def format_trigger_info_query_statement(self, expr: "TriggerInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format single trigger information query.

        Args:
            expr: Trigger info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If trigger introspection is not supported.
        """
        if not self.supports_trigger_introspection():
            raise UnsupportedFeatureError(self.name, "trigger introspection")
        raise NotImplementedError("Subclass must implement format_trigger_info_query_statement")


class OperationalStatsIntrospectionMixin:
    """
    Mixin for operational statistics capability declaration.

    Every probe here asks about measured behaviour -- counters, usage, the
    dependency graph -- rather than declared structure. This base answers
    False for all of them and refuses the formatters, so a dialect that keeps
    no statistic says so rather than returning an empty answer.
    """

    # ========== Capability Detection ==========

    def supports_runtime_stats(self) -> bool:
        """Whether runtime statistics introspection is supported. Defaults to False."""
        return False

    def supports_index_stats(self) -> bool:
        """Whether index statistics introspection is supported. Defaults to False."""
        return False

    def supports_table_stats(self) -> bool:
        """Whether table statistics introspection is supported. Defaults to False."""
        return False

    def supports_unused_indexes_detection(self) -> bool:
        """Whether unused indexes detection is supported. Defaults to False.

        Answering ``True`` obliges ``format_unused_indexes_query_statement``
        to render. What "unused" means is the backend's to state: counters
        reset, views cover only the statistics they can see, and an index
        missing from the answer is absence of evidence, never proof of use.
        """
        return False

    def supports_object_dependencies(self) -> bool:
        """Whether object dependencies introspection is supported. Defaults to False."""
        return False

    # ========== Query Formatting ==========

    def format_unused_indexes_query_statement(
        self, expr: "UnusedIndexesQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_unused_indexes_query_statement")

    def format_table_usage_stats_query_statement(
        self, expr: "TableUsageStatsQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_table_usage_stats_query_statement")

    def format_runtime_metrics_query_statement(
        self, expr: "RuntimeMetricsQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_runtime_metrics_query_statement")

    def format_index_usage_stats_query_statement(
        self, expr: "IndexUsageStatsQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_index_usage_stats_query_statement")

    def format_object_dependency_query_statement(
        self, expr: "ObjectDependencyQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_object_dependency_query_statement")


class DataProfileIntrospectionMixin:
    """
    Mixin for column data profiling capability declaration.

    These questions read the rows rather than the declaration. This base
    answers False for all of them and refuses the formatters.
    """

    # ========== Capability Detection ==========

    def supports_column_data_profile(self) -> bool:
        """Whether a column's *data* can be profiled. Defaults to False.

        Answering ``True`` obliges
        ``format_column_data_profile_query_statement`` to render, and the
        answer to carry provenance: an estimate from a statistics catalogue and
        an exact count are different facts wearing the same slot name.
        """
        return False

    def supports_column_value_sample(self) -> bool:
        """Whether a column's most frequent values are answerable. Defaults to False.

        Kept apart from the data profile because the two cost differently on
        every engine: a catalogue answers the profile for free, while a value
        listing either comes from a kept ``most_common_vals`` list or has to
        aggregate.
        """
        return False

    def supports_join_coverage(self) -> bool:
        """Whether two columns' value domains can be compared. Defaults to False.

        The most expensive probe of the family and the only one about a
        *relation* rather than an object; a backend that cannot read both
        columns should answer False rather than approximate.
        """
        return False

    # ========== Query Formatting ==========

    def format_column_data_profile_query_statement(
        self, expr: "ColumnDataProfileQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_column_data_profile_query_statement")

    def format_column_value_sample_query_statement(
        self, expr: "ColumnValueSampleQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_column_value_sample_query_statement")

    def format_join_coverage_query_statement(
        self, expr: "JoinCoverageQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_join_coverage_query_statement")


class DdlExtractionIntrospectionMixin:
    """
    Mixin for DDL extraction capability declaration.

    An engine answers this only if it can return the statement text that
    recreates an object, or assemble one from the catalogue. This base
    answers False and refuses the formatter.
    """

    # ========== Capability Detection ==========

    def supports_ddl_extraction(self) -> bool:
        """Whether DDL extraction is supported. Defaults to False."""
        return False

    def supports_ddl_extraction_native(self) -> bool:
        """Whether native DDL extraction is supported (False means assembly required).

        Defaults to False.
        """
        return False

    # ========== Query Formatting ==========

    def format_ddl_statement_query_statement(
        self, expr: "DDLStatementQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_ddl_statement_query_statement")


class IntrospectionMixin(
    StructureIntrospectionMixin,
    OperationalStatsIntrospectionMixin,
    DataProfileIntrospectionMixin,
    DdlExtractionIntrospectionMixin,
):
    """Composition-only aggregate of the four introspection capability mixins.

    Declares no members of its own: a dialect composes this to answer every
    introspection family, and every method it resolves is a family's answer,
    so an override anywhere in a dialect's bases keeps winning exactly as it
    did before the split.
    """


class AsyncStructureIntrospectionMixin:
    """
    Async version of StructureIntrospectionMixin with symmetric API.

    Dialects declare capabilities (supports_* methods) and provide format_*
    methods to generate database-specific SQL for structure queries.

    Note: The format_* methods are synchronous even in async context because
    they only generate SQL strings without database I/O.
    """

    # ========== Capability Detection ==========

    def supports_introspection(self) -> bool:
        """Whether introspection is supported. Defaults to False."""
        return False

    def supports_database_info(self) -> bool:
        """Whether database information query is supported. Defaults to False."""
        return False

    def supports_table_introspection(self) -> bool:
        """Whether table introspection is supported. Defaults to False."""
        return False

    def supports_column_introspection(self) -> bool:
        """Whether column introspection is supported. Defaults to False."""
        return False

    def supports_index_introspection(self) -> bool:
        """Whether index introspection is supported. Defaults to False."""
        return False

    def supports_foreign_key_introspection(self) -> bool:
        """Whether foreign key introspection is supported. Defaults to False."""
        return False

    def supports_view_introspection(self) -> bool:
        """Whether view introspection is supported. Defaults to False."""
        return False

    def supports_trigger_introspection(self) -> bool:
        """Whether trigger introspection is supported. Defaults to False."""
        return False

    def supports_extensions(self) -> bool:
        """Whether this engine exposes a catalogue of installed add-on components.

        Defaults to ``False``. ``extension`` is not SQL-standard vocabulary and
        the concept differs per engine -- PostgreSQL's are ``CREATE EXTENSION``
        packages with a version and a schema, SQLite's are registered virtual
        table modules -- so a ``True`` promises that the engine *will answer*,
        not *what shape the answer takes*. Read the backend's own docs and
        result type before relying on any field; see
        :class:`~...protocols.introspect.structure.AsyncStructureIntrospectionSupport`
        for why the name stays in core despite that.
        """
        return False

    def supports_table_storage_introspection(self) -> bool:
        """Whether per-table storage metrics introspection is supported. Defaults to False."""
        return False

    # ========== Query Formatting ==========

    def format_database_info_query_statement(self, expr: "DatabaseInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format database information query.

        Args:
            expr: Database info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If database info query is not supported.
        """
        if not self.supports_database_info():
            raise UnsupportedFeatureError(self.name, "database info query")
        raise NotImplementedError("Subclass must implement format_database_info_query_statement")

    def format_table_list_query_statement(self, expr: "TableListQueryStatement") -> Tuple[str, tuple]:
        """
        Format table list query.

        Args:
            expr: Table list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If table introspection is not supported.
        """
        if not self.supports_table_introspection():
            raise UnsupportedFeatureError(self.name, "table introspection")
        raise NotImplementedError("Subclass must implement format_table_list_query_statement")

    def format_table_info_query_statement(self, expr: "TableInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format single table information query.

        Args:
            expr: Table info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If table introspection is not supported.
        """
        if not self.supports_table_introspection():
            raise UnsupportedFeatureError(self.name, "table introspection")
        raise NotImplementedError("Subclass must implement format_table_info_query_statement")

    def format_column_info_query_statement(self, expr: "ColumnInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format column information query.

        Args:
            expr: Column info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If column introspection is not supported.
        """
        if not self.supports_column_introspection():
            raise UnsupportedFeatureError(self.name, "column introspection")
        raise NotImplementedError("Subclass must implement format_column_info_query_statement")

    def format_index_info_query_statement(self, expr: "IndexInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format index information query.

        Args:
            expr: Index info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If index introspection is not supported.
        """
        if not self.supports_index_introspection():
            raise UnsupportedFeatureError(self.name, "index introspection")
        raise NotImplementedError("Subclass must implement format_index_info_query_statement")

    def format_foreign_key_query_statement(self, expr: "ForeignKeyQueryStatement") -> Tuple[str, tuple]:
        """
        Format foreign key information query.

        Args:
            expr: Foreign key expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If foreign key introspection is not supported.
        """
        if not self.supports_foreign_key_introspection():
            raise UnsupportedFeatureError(self.name, "foreign key introspection")
        raise NotImplementedError("Subclass must implement format_foreign_key_query_statement")

    def format_view_list_query_statement(self, expr: "ViewListQueryStatement") -> Tuple[str, tuple]:
        """
        Format view list query.

        Args:
            expr: View list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If view introspection is not supported.
        """
        if not self.supports_view_introspection():
            raise UnsupportedFeatureError(self.name, "view introspection")
        raise NotImplementedError("Subclass must implement format_view_list_query_statement")

    def format_view_info_query_statement(self, expr: "ViewInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format single view information query.

        Args:
            expr: View info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If view introspection is not supported.
        """
        if not self.supports_view_introspection():
            raise UnsupportedFeatureError(self.name, "view introspection")
        raise NotImplementedError("Subclass must implement format_view_info_query_statement")

    def format_trigger_list_query_statement(self, expr: "TriggerListQueryStatement") -> Tuple[str, tuple]:
        """
        Format trigger list query.

        Args:
            expr: Trigger list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If trigger introspection is not supported.
        """
        if not self.supports_trigger_introspection():
            raise UnsupportedFeatureError(self.name, "trigger introspection")
        raise NotImplementedError("Subclass must implement format_trigger_list_query_statement")

    def format_trigger_info_query_statement(self, expr: "TriggerInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format single trigger information query.

        Args:
            expr: Trigger info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If trigger introspection is not supported.
        """
        if not self.supports_trigger_introspection():
            raise UnsupportedFeatureError(self.name, "trigger introspection")
        raise NotImplementedError("Subclass must implement format_trigger_info_query_statement")


class AsyncOperationalStatsIntrospectionMixin:
    """
    Async version of OperationalStatsIntrospectionMixin with symmetric API.

    The format_* methods are synchronous even in async context: they only
    generate SQL strings without database I/O.
    """

    # ========== Capability Detection ==========

    def supports_runtime_stats(self) -> bool:
        """Whether runtime statistics introspection is supported. Defaults to False."""
        return False

    def supports_index_stats(self) -> bool:
        """Whether index statistics introspection is supported. Defaults to False."""
        return False

    def supports_table_stats(self) -> bool:
        """Whether table statistics introspection is supported. Defaults to False."""
        return False

    def supports_unused_indexes_detection(self) -> bool:
        """Whether unused indexes detection is supported. Defaults to False.

        Answering ``True`` obliges ``format_unused_indexes_query_statement``
        to render. What "unused" means is the backend's to state: counters
        reset, views cover only the statistics they can see, and an index
        missing from the answer is absence of evidence, never proof of use.
        """
        return False

    def supports_object_dependencies(self) -> bool:
        """Whether object dependencies introspection is supported. Defaults to False."""
        return False

    # ========== Query Formatting ==========

    def format_unused_indexes_query_statement(
        self, expr: "UnusedIndexesQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_unused_indexes_query_statement")

    def format_table_usage_stats_query_statement(
        self, expr: "TableUsageStatsQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_table_usage_stats_query_statement")

    def format_runtime_metrics_query_statement(
        self, expr: "RuntimeMetricsQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_runtime_metrics_query_statement")

    def format_index_usage_stats_query_statement(
        self, expr: "IndexUsageStatsQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_index_usage_stats_query_statement")

    def format_object_dependency_query_statement(
        self, expr: "ObjectDependencyQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_object_dependency_query_statement")


class AsyncDataProfileIntrospectionMixin:
    """
    Async version of DataProfileIntrospectionMixin with symmetric API.

    The format_* methods are synchronous even in async context: they only
    generate SQL strings without database I/O.
    """

    # ========== Capability Detection ==========

    def supports_column_data_profile(self) -> bool:
        """Whether a column's *data* can be profiled. Defaults to False.

        Answering ``True`` obliges
        ``format_column_data_profile_query_statement`` to render, and the
        answer to carry provenance: an estimate from a statistics catalogue and
        an exact count are different facts wearing the same slot name.
        """
        return False

    def supports_column_value_sample(self) -> bool:
        """Whether a column's most frequent values are answerable. Defaults to False.

        Kept apart from the data profile because the two cost differently on
        every engine: a catalogue answers the profile for free, while a value
        listing either comes from a kept ``most_common_vals`` list or has to
        aggregate.
        """
        return False

    def supports_join_coverage(self) -> bool:
        """Whether two columns' value domains can be compared. Defaults to False.

        The most expensive probe of the family and the only one about a
        *relation* rather than an object; a backend that cannot read both
        columns should answer False rather than approximate.
        """
        return False

    # ========== Query Formatting ==========

    def format_column_data_profile_query_statement(
        self, expr: "ColumnDataProfileQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_column_data_profile_query_statement")

    def format_column_value_sample_query_statement(
        self, expr: "ColumnValueSampleQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_column_value_sample_query_statement")

    def format_join_coverage_query_statement(
        self, expr: "JoinCoverageQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_join_coverage_query_statement")


class AsyncDdlExtractionIntrospectionMixin:
    """
    Async version of DdlExtractionIntrospectionMixin with symmetric API.

    The formatter is synchronous even in async context: it only generates a
    SQL string without database I/O.
    """

    # ========== Capability Detection ==========

    def supports_ddl_extraction(self) -> bool:
        """Whether DDL extraction is supported. Defaults to False."""
        return False

    def supports_ddl_extraction_native(self) -> bool:
        """Whether native DDL extraction is supported (False means assembly required).

        Defaults to False.
        """
        return False

    # ========== Query Formatting ==========

    def format_ddl_statement_query_statement(
        self, expr: "DDLStatementQueryStatement"
    ) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(self.name, "format_ddl_statement_query_statement")


class AsyncIntrospectionMixin(
    AsyncStructureIntrospectionMixin,
    AsyncOperationalStatsIntrospectionMixin,
    AsyncDataProfileIntrospectionMixin,
    AsyncDdlExtractionIntrospectionMixin,
):
    """Composition-only async aggregate of the four introspection capability mixins.

    Declares no members of its own, for the same reason the synchronous
    aggregate declares none.
    """
