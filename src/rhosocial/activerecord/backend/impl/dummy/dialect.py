# src/rhosocial/activerecord/backend/impl/dummy/dialect.py
"""
Dummy backend SQL dialect implementation.

This dialect implements all protocols and supports all features.
It is used for to_sql() testing and does not involve actual database connections.

Architecture Notes:
===================

The dialect mixins in rhosocial.activerecord.backend.dialect.mixins provide
standard SQL implementations for various features. Each mixin includes:

1. supports_* methods: Return False by default, indicating the feature is
   not supported. Concrete dialects override these to enable features.

2. format_* methods: Provide standard SQL generation for the feature.
   These follow SQL standard syntax and are designed to work with the
   Expression classes in rhosocial.activerecord.backend.expression.

This DummyDialect class serves a specific purpose:

- It inherits ALL mixins to provide complete SQL standard coverage
- It overrides ALL supports_* methods to return True, effectively
  "enabling all switches"
- No additional format_* implementations are needed since the mixins
  already provide standard SQL generation

In essence, this file is a "switch board" that combines all mixins and
turns on every feature flag. The actual SQL generation logic resides in
the mixin classes, making this dialect a pure composition of standard
SQL capabilities.

For concrete database dialects (PostgreSQL, MySQL, etc.), they would:
1. Inherit the same mixins
2. Override supports_* methods based on actual database capabilities
3. Override format_* methods where the database deviates from SQL standard
"""
from typing import List

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.protocols import (
    WindowFunctionSupport, CTESupport, AdvancedGroupingSupport, ReturningSupport,
    UpsertSupport, LateralJoinSupport, ArraySupport, JSONSupport, ExplainSupport,
    FilterClauseSupport, OrderedSetAggregationSupport, MergeSupport,
    TemporalTableSupport, QualifyClauseSupport, LockingSupport, GraphSupport,
    JoinSupport, SetOperationSupport, ILIKESupport,
    # DDL Protocols
    TableSupport, ViewSupport, TruncateSupport, SchemaSupport,
    IndexSupport, SequenceSupport, TriggerSupport, FunctionSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    WindowFunctionMixin, CTEMixin, AdvancedGroupingMixin, ReturningMixin,
    UpsertMixin, LateralJoinMixin, ArrayMixin, JSONMixin, ExplainMixin,
    FilterClauseMixin, OrderedSetAggregationMixin, MergeMixin,
    TemporalTableMixin, QualifyClauseMixin, LockingMixin, GraphMixin, JoinMixin,
    SetOperationMixin, ILIKEMixin,
    # DDL Mixins
    TableMixin, ViewMixin, TruncateMixin, SchemaMixin,
    IndexMixin, SequenceMixin, TriggerMixin, FunctionMixin,
)


class DummyDialect(
    SQLDialectBase,
    WindowFunctionMixin, CTEMixin, AdvancedGroupingMixin, ReturningMixin,
    UpsertMixin, LateralJoinMixin, ArrayMixin, JSONMixin, ExplainMixin,
    FilterClauseMixin, OrderedSetAggregationMixin, MergeMixin,
    TemporalTableMixin, QualifyClauseMixin, LockingMixin, GraphMixin,
    JoinMixin, SetOperationMixin, ILIKEMixin,
    # DDL Mixins
    TableMixin, ViewMixin, TruncateMixin, SchemaMixin,
    IndexMixin, SequenceMixin, TriggerMixin, FunctionMixin,
    # Protocols for type checking
    WindowFunctionSupport, CTESupport, AdvancedGroupingSupport, ReturningSupport,
    UpsertSupport, LateralJoinSupport, ArraySupport, JSONSupport, ExplainSupport,
    FilterClauseSupport, OrderedSetAggregationSupport, MergeSupport,
    TemporalTableSupport, QualifyClauseSupport, LockingSupport, GraphSupport,
    JoinSupport, SetOperationSupport, ILIKESupport,
    # DDL Protocols
    TableSupport, ViewSupport, TruncateSupport, SchemaSupport,
    IndexSupport, SequenceSupport, TriggerSupport, FunctionSupport,
):
    """
    Dummy dialect supporting all features for SQL generation testing.
    """

    # region Protocol Support Checks - Core Features
    def supports_window_functions(self) -> bool: return True
    def supports_window_frame_clause(self) -> bool: return True
    def supports_basic_cte(self) -> bool: return True
    def supports_recursive_cte(self) -> bool: return True
    def supports_materialized_cte(self) -> bool: return True
    def supports_rollup(self) -> bool: return True
    def supports_cube(self) -> bool: return True
    def supports_grouping_sets(self) -> bool: return True
    def supports_returning_clause(self) -> bool: return True
    def supports_upsert(self) -> bool: return True
    def get_upsert_syntax_type(self) -> str: return "ON CONFLICT"
    def supports_lateral_join(self) -> bool: return True
    def supports_array_type(self) -> bool: return True
    def supports_array_constructor(self) -> bool: return True
    def supports_array_access(self) -> bool: return True
    def supports_json_type(self) -> bool: return True
    def get_json_access_operator(self) -> str: return "->"
    def supports_json_table(self) -> bool: return True
    def supports_explain_analyze(self) -> bool: return True
    def supports_explain_format(self, format_type: str) -> bool: return True
    def supports_filter_clause(self) -> bool: return True
    def supports_ordered_set_aggregation(self) -> bool: return True
    def supports_merge_statement(self) -> bool: return True
    def supports_temporal_tables(self) -> bool: return True
    def supports_qualify_clause(self) -> bool: return True
    def supports_for_update_skip_locked(self) -> bool: return True
    def supports_graph_match(self) -> bool: return True
    def supports_inner_join(self) -> bool: return True
    def supports_left_join(self) -> bool: return True
    def supports_right_join(self) -> bool: return True
    def supports_full_join(self) -> bool: return True
    def supports_cross_join(self) -> bool: return True
    def supports_natural_join(self) -> bool: return True
    def supports_union(self) -> bool: return True
    def supports_union_all(self) -> bool: return True
    def supports_intersect(self) -> bool: return True
    def supports_except(self) -> bool: return True
    def supports_set_operation_order_by(self) -> bool: return True
    def supports_set_operation_limit_offset(self) -> bool: return True
    def supports_set_operation_for_update(self) -> bool: return True
    def supports_ilike(self) -> bool: return True
    # endregion

    # region Table DDL Support
    def supports_create_table(self) -> bool: return True
    def supports_drop_table(self) -> bool: return True
    def supports_alter_table(self) -> bool: return True
    def supports_temporary_table(self) -> bool: return True
    def supports_if_not_exists_table(self) -> bool: return True
    def supports_if_exists_table(self) -> bool: return True
    def supports_table_partitioning(self) -> bool: return True
    def supports_table_tablespace(self) -> bool: return True
    def supports_drop_column(self) -> bool: return True
    def supports_alter_column_type(self) -> bool: return True
    def supports_rename_column(self) -> bool: return True
    def supports_rename_table(self) -> bool: return True
    def supports_add_constraint(self) -> bool: return True
    def supports_drop_constraint(self) -> bool: return True
    # endregion

    # region View DDL Support
    def supports_create_view(self) -> bool: return True
    def supports_drop_view(self) -> bool: return True
    def supports_or_replace_view(self) -> bool: return True
    def supports_temporary_view(self) -> bool: return True
    def supports_materialized_view(self) -> bool: return True
    def supports_refresh_materialized_view(self) -> bool: return True
    def supports_materialized_view_tablespace(self) -> bool: return True
    def supports_materialized_view_storage_options(self) -> bool: return True
    def supports_if_exists_view(self) -> bool: return True
    def supports_view_check_option(self) -> bool: return True
    def supports_cascade_view(self) -> bool: return True
    # endregion

    # region Truncate DDL Support
    def supports_truncate(self) -> bool: return True
    def supports_truncate_table_keyword(self) -> bool: return True
    def supports_truncate_restart_identity(self) -> bool: return True
    def supports_truncate_cascade(self) -> bool: return True
    # endregion

    # region Schema DDL Support
    def supports_create_schema(self) -> bool: return True
    def supports_drop_schema(self) -> bool: return True
    def supports_schema_if_not_exists(self) -> bool: return True
    def supports_schema_if_exists(self) -> bool: return True
    def supports_schema_cascade(self) -> bool: return True
    def supports_schema_authorization(self) -> bool: return True
    # endregion

    # region Index DDL Support
    def supports_create_index(self) -> bool: return True
    def supports_drop_index(self) -> bool: return True
    def supports_unique_index(self) -> bool: return True
    def supports_index_if_not_exists(self) -> bool: return True
    def supports_index_if_exists(self) -> bool: return True
    def supports_index_type(self) -> bool: return True
    def supports_partial_index(self) -> bool: return True
    def supports_functional_index(self) -> bool: return True
    def supports_index_include(self) -> bool: return True
    def supports_index_tablespace(self) -> bool: return True
    def supports_concurrent_index(self) -> bool: return True

    def get_supported_index_types(self) -> List[str]:
        return ['BTREE', 'HASH', 'GIN', 'GIST', 'SPGIST', 'BRIN']
    # endregion

    # region Sequence DDL Support
    def supports_sequence(self) -> bool: return True
    def supports_create_sequence(self) -> bool: return True
    def supports_drop_sequence(self) -> bool: return True
    def supports_alter_sequence(self) -> bool: return True
    def supports_sequence_if_not_exists(self) -> bool: return True
    def supports_sequence_if_exists(self) -> bool: return True
    def supports_sequence_cycle(self) -> bool: return True
    def supports_sequence_cache(self) -> bool: return True
    def supports_sequence_order(self) -> bool: return True
    def supports_sequence_owned_by(self) -> bool: return True
    # endregion

    # region Trigger DDL Support
    def supports_trigger(self) -> bool: return True
    def supports_create_trigger(self) -> bool: return True
    def supports_drop_trigger(self) -> bool: return True
    def supports_instead_of_trigger(self) -> bool: return True
    def supports_statement_trigger(self) -> bool: return True
    def supports_trigger_referencing(self) -> bool: return True
    def supports_trigger_when(self) -> bool: return True
    def supports_trigger_if_not_exists(self) -> bool: return True
    # endregion

    # region Function DDL Support
    def supports_function(self) -> bool: return True
    def supports_create_function(self) -> bool: return True
    def supports_drop_function(self) -> bool: return True
    def supports_function_or_replace(self) -> bool: return True
    def supports_function_parameters(self) -> bool: return True
    # endregion
