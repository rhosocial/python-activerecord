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
    WindowFunctionSupport,
    CTESupport,
    AdvancedGroupingSupport,
    ReturningSupport,
    UpsertSupport,
    LateralJoinSupport,
    ArraySupport,
    JSONSupport,
    ExplainSupport,
    FilterClauseSupport,
    OrderedSetAggregationSupport,
    MergeSupport,
    TemporalTableSupport,
    QualifyClauseSupport,
    LockingSupport,
    GraphSupport,
    JoinSupport,
    SetOperationSupport,
    ILIKESupport,
    # DDL Protocols
    TableSupport,
    ViewSupport,
    TruncateSupport,
    SchemaSupport,
    IndexSupport,
    SequenceSupport,
    TriggerSupport,
    FunctionSupport,
    GeneratedColumnSupport,
    # Introspection Protocols
    IntrospectionSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    WindowFunctionMixin,
    CTEMixin,
    AdvancedGroupingMixin,
    ReturningMixin,
    UpsertMixin,
    LateralJoinMixin,
    ArrayMixin,
    JSONMixin,
    ExplainMixin,
    FilterClauseMixin,
    OrderedSetAggregationMixin,
    MergeMixin,
    TemporalTableMixin,
    QualifyClauseMixin,
    LockingMixin,
    GraphMixin,
    JoinMixin,
    SetOperationMixin,
    ILIKEMixin,
    # DDL Mixins
    TableMixin,
    ViewMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TriggerMixin,
    FunctionMixin,
    GeneratedColumnMixin,
    # Introspection Mixin
    IntrospectionMixin,
)


class DummyDialect(
    SQLDialectBase,
    WindowFunctionMixin,
    CTEMixin,
    AdvancedGroupingMixin,
    ReturningMixin,
    UpsertMixin,
    LateralJoinMixin,
    ArrayMixin,
    JSONMixin,
    ExplainMixin,
    FilterClauseMixin,
    OrderedSetAggregationMixin,
    MergeMixin,
    TemporalTableMixin,
    QualifyClauseMixin,
    LockingMixin,
    GraphMixin,
    JoinMixin,
    SetOperationMixin,
    ILIKEMixin,
    # DDL Mixins
    TableMixin,
    ViewMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TriggerMixin,
    FunctionMixin,
    GeneratedColumnMixin,
    # Introspection Mixin
    IntrospectionMixin,
    # Protocols for type checking
    WindowFunctionSupport,
    CTESupport,
    AdvancedGroupingSupport,
    ReturningSupport,
    UpsertSupport,
    LateralJoinSupport,
    ArraySupport,
    JSONSupport,
    ExplainSupport,
    FilterClauseSupport,
    OrderedSetAggregationSupport,
    MergeSupport,
    TemporalTableSupport,
    QualifyClauseSupport,
    LockingSupport,
    GraphSupport,
    JoinSupport,
    SetOperationSupport,
    ILIKESupport,
    # DDL Protocols
    TableSupport,
    ViewSupport,
    TruncateSupport,
    SchemaSupport,
    IndexSupport,
    SequenceSupport,
    TriggerSupport,
    FunctionSupport,
    GeneratedColumnSupport,
    # Introspection Protocols
    IntrospectionSupport,
):
    """
    Dummy dialect supporting all features for SQL generation testing.
    """

    # region Protocol Support Checks - Core Features
    def supports_window_functions(self) -> bool:
        return True

    def supports_window_frame_clause(self) -> bool:
        return True

    def supports_basic_cte(self) -> bool:
        return True

    def supports_recursive_cte(self) -> bool:
        return True

    def supports_materialized_cte(self) -> bool:
        return True

    def supports_rollup(self) -> bool:
        return True

    def supports_cube(self) -> bool:
        return True

    def supports_grouping_sets(self) -> bool:
        return True

    def supports_returning_clause(self) -> bool:
        return True

    def supports_upsert(self) -> bool:
        return True

    def get_upsert_syntax_type(self) -> str:
        return "ON CONFLICT"

    def supports_lateral_join(self) -> bool:
        return True

    def supports_array_type(self) -> bool:
        return True

    def supports_array_constructor(self) -> bool:
        return True

    def supports_array_access(self) -> bool:
        return True

    def supports_json_type(self) -> bool:
        return True

    def get_json_access_operator(self) -> str:
        return "->"

    def supports_json_table(self) -> bool:
        return True

    def supports_explain_analyze(self) -> bool:
        return True

    def supports_explain_format(self, format_type: str) -> bool:
        return True

    def supports_filter_clause(self) -> bool:
        return True

    def supports_ordered_set_aggregation(self) -> bool:
        return True

    def supports_merge_statement(self) -> bool:
        return True

    def supports_temporal_tables(self) -> bool:
        return True

    def supports_qualify_clause(self) -> bool:
        return True

    def supports_for_update_skip_locked(self) -> bool:
        return True

    def supports_graph_match(self) -> bool:
        return True

    def supports_inner_join(self) -> bool:
        return True

    def supports_left_join(self) -> bool:
        return True

    def supports_right_join(self) -> bool:
        return True

    def supports_full_join(self) -> bool:
        return True

    def supports_cross_join(self) -> bool:
        return True

    def supports_natural_join(self) -> bool:
        return True

    def supports_explicit_inner_join(self) -> bool:
        return True

    def supports_union(self) -> bool:
        return True

    def supports_union_all(self) -> bool:
        return True

    def supports_intersect(self) -> bool:
        return True

    def supports_except(self) -> bool:
        return True

    def supports_set_operation_order_by(self) -> bool:
        return True

    def supports_set_operation_limit_offset(self) -> bool:
        return True

    def supports_set_operation_for_update(self) -> bool:
        return True

    def supports_ilike(self) -> bool:
        return True

    def supports_offset_without_limit(self) -> bool:
        return True

    # endregion

    # region Table DDL Support
    def supports_create_table(self) -> bool:
        return True

    def supports_drop_table(self) -> bool:
        return True

    def supports_alter_table(self) -> bool:
        return True

    def supports_temporary_table(self) -> bool:
        return True

    def supports_if_not_exists_table(self) -> bool:
        return True

    def supports_if_exists_table(self) -> bool:
        return True

    def supports_table_partitioning(self) -> bool:
        return True

    def supports_table_tablespace(self) -> bool:
        return True

    def supports_drop_column(self) -> bool:
        return True

    def supports_alter_column_type(self) -> bool:
        return True

    def supports_rename_column(self) -> bool:
        return True

    def supports_rename_table(self) -> bool:
        return True

    def supports_add_constraint(self) -> bool:
        return True

    def supports_drop_constraint(self) -> bool:
        return True

    # endregion

    # region View DDL Support
    def supports_create_view(self) -> bool:
        return True

    def supports_drop_view(self) -> bool:
        return True

    def supports_or_replace_view(self) -> bool:
        return True

    def supports_temporary_view(self) -> bool:
        return True

    def supports_materialized_view(self) -> bool:
        return True

    def supports_refresh_materialized_view(self) -> bool:
        return True

    def supports_materialized_view_tablespace(self) -> bool:
        return True

    def supports_materialized_view_storage_options(self) -> bool:
        return True

    def supports_if_exists_view(self) -> bool:
        return True

    def supports_view_check_option(self) -> bool:
        return True

    def supports_cascade_view(self) -> bool:
        return True

    # endregion

    # region Truncate DDL Support
    def supports_truncate(self) -> bool:
        return True

    def supports_truncate_table_keyword(self) -> bool:
        return True

    def supports_truncate_restart_identity(self) -> bool:
        return True

    def supports_truncate_cascade(self) -> bool:
        return True

    # endregion

    # region Schema DDL Support
    def supports_create_schema(self) -> bool:
        return True

    def supports_drop_schema(self) -> bool:
        return True

    def supports_schema_if_not_exists(self) -> bool:
        return True

    def supports_schema_if_exists(self) -> bool:
        return True

    def supports_schema_cascade(self) -> bool:
        return True

    def supports_schema_authorization(self) -> bool:
        return True

    # endregion

    # region Index DDL Support
    def supports_create_index(self) -> bool:
        return True

    def supports_drop_index(self) -> bool:
        return True

    def supports_unique_index(self) -> bool:
        return True

    def supports_index_if_not_exists(self) -> bool:
        return True

    def supports_index_if_exists(self) -> bool:
        return True

    def supports_index_type(self) -> bool:
        return True

    def supports_partial_index(self) -> bool:
        return True

    def supports_functional_index(self) -> bool:
        return True

    def supports_index_include(self) -> bool:
        return True

    def supports_index_tablespace(self) -> bool:
        return True

    def supports_concurrent_index(self) -> bool:
        return True

    def supports_fulltext_index(self) -> bool:
        return True

    def supports_fulltext_parser(self) -> bool:
        return True

    def supports_fulltext_boolean_mode(self) -> bool:
        return True

    def supports_fulltext_query_expansion(self) -> bool:
        return True

    def get_supported_index_types(self) -> List[str]:
        return ["BTREE", "HASH", "GIN", "GIST", "SPGIST", "BRIN"]

    # endregion

    # region Sequence DDL Support
    def supports_sequence(self) -> bool:
        return True

    def supports_create_sequence(self) -> bool:
        return True

    def supports_drop_sequence(self) -> bool:
        return True

    def supports_alter_sequence(self) -> bool:
        return True

    def supports_sequence_if_not_exists(self) -> bool:
        return True

    def supports_sequence_if_exists(self) -> bool:
        return True

    def supports_sequence_cycle(self) -> bool:
        return True

    def supports_sequence_cache(self) -> bool:
        return True

    def supports_sequence_order(self) -> bool:
        return True

    def supports_sequence_owned_by(self) -> bool:
        return True

    # endregion

    # region Trigger DDL Support
    def supports_trigger(self) -> bool:
        return True

    def supports_create_trigger(self) -> bool:
        return True

    def supports_drop_trigger(self) -> bool:
        return True

    def supports_instead_of_trigger(self) -> bool:
        return True

    def supports_statement_trigger(self) -> bool:
        return True

    def supports_trigger_referencing(self) -> bool:
        return True

    def supports_trigger_when(self) -> bool:
        return True

    def supports_trigger_if_not_exists(self) -> bool:
        return True

    # endregion

    # region Function DDL Support
    def supports_function(self) -> bool:
        return True

    def supports_create_function(self) -> bool:
        return True

    def supports_drop_function(self) -> bool:
        return True

    def supports_function_or_replace(self) -> bool:
        return True

    def supports_function_parameters(self) -> bool:
        return True

    # endregion

    # region Generated Column Support
    def supports_generated_columns(self) -> bool:
        return True

    def supports_stored_generated_columns(self) -> bool:
        return True

    def supports_virtual_generated_columns(self) -> bool:
        return True

    # endregion

    # region Introspection Support
    def supports_introspection(self) -> bool:
        return True

    def supports_database_info(self) -> bool:
        return True

    def supports_table_introspection(self) -> bool:
        return True

    def supports_column_introspection(self) -> bool:
        return True

    def supports_index_introspection(self) -> bool:
        return True

    def supports_foreign_key_introspection(self) -> bool:
        return True

    def supports_view_introspection(self) -> bool:
        return True

    def supports_trigger_introspection(self) -> bool:
        return True

    def get_supported_introspection_scopes(self):
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope
        return [
            IntrospectionScope.DATABASE,
            IntrospectionScope.TABLE,
            IntrospectionScope.COLUMN,
            IntrospectionScope.INDEX,
            IntrospectionScope.FOREIGN_KEY,
            IntrospectionScope.VIEW,
            IntrospectionScope.TRIGGER,
        ]

    # ========== Introspection Query Formatting ==========

    def format_database_info_query(self, expr) -> tuple:
        """Format database info query (SQL standard)."""
        return ("SELECT CURRENT_DATABASE() AS name, CURRENT_USER AS owner", ())

    def format_table_list_query(self, expr) -> tuple:
        """Format table list query (SQL standard)."""
        schema = expr.get_param('schema') if hasattr(expr, 'get_param') else None
        if schema:
            return (f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema}'", ())
        return ("SELECT table_name FROM information_schema.tables WHERE table_schema = CURRENT_SCHEMA()", ())

    def format_table_info_query(self, expr) -> tuple:
        """Format table info query (SQL standard)."""
        table_name = expr.get_param('table_name') if hasattr(expr, 'get_param') else None
        schema = expr.get_param('schema') if hasattr(expr, 'get_param') else None
        schema_cond = f" AND table_schema = '{schema}'" if schema else ""
        return (f"SELECT * FROM information_schema.tables WHERE table_name = '{table_name}'{schema_cond}", ())

    def format_column_info_query(self, expr) -> tuple:
        """Format column info query (SQL standard)."""
        table_name = expr.get_param('table_name') if hasattr(expr, 'get_param') else None
        schema = expr.get_param('schema') if hasattr(expr, 'get_param') else None
        schema_cond = f" AND table_schema = '{schema}'" if schema else ""
        return (f"SELECT * FROM information_schema.columns WHERE table_name = '{table_name}'{schema_cond} ORDER BY ordinal_position", ())

    def format_index_info_query(self, expr) -> tuple:
        """Format index info query (SQL standard)."""
        table_name = expr.get_param('table_name') if hasattr(expr, 'get_param') else None
        return (f"SELECT * FROM information_schema.statistics WHERE table_name = '{table_name}'", ())

    def format_foreign_key_query(self, expr) -> tuple:
        """Format foreign key query (SQL standard)."""
        table_name = expr.get_param('table_name') if hasattr(expr, 'get_param') else None
        return (f"SELECT * FROM information_schema.table_constraints WHERE table_name = '{table_name}' AND constraint_type = 'FOREIGN KEY'", ())

    def format_view_list_query(self, expr) -> tuple:
        """Format view list query (SQL standard)."""
        schema = expr.get_param('schema') if hasattr(expr, 'get_param') else None
        if schema:
            return (f"SELECT table_name FROM information_schema.views WHERE table_schema = '{schema}'", ())
        return ("SELECT table_name FROM information_schema.views WHERE table_schema = CURRENT_SCHEMA()", ())

    def format_view_info_query(self, expr) -> tuple:
        """Format view info query (SQL standard)."""
        view_name = expr.get_param('view_name') if hasattr(expr, 'get_param') else None
        schema = expr.get_param('schema') if hasattr(expr, 'get_param') else None
        schema_cond = f" AND table_schema = '{schema}'" if schema else ""
        return (f"SELECT * FROM information_schema.views WHERE table_name = '{view_name}'{schema_cond}", ())

    def format_trigger_list_query(self, expr) -> tuple:
        """Format trigger list query (SQL standard)."""
        table_name = expr.get_param('table_name') if hasattr(expr, 'get_param') else None
        return (f"SELECT * FROM information_schema.triggers WHERE event_object_table = '{table_name}'", ())

    def format_trigger_info_query(self, expr) -> tuple:
        """Format trigger info query (SQL standard)."""
        trigger_name = expr.get_param('trigger_name') if hasattr(expr, 'get_param') else None
        return (f"SELECT * FROM information_schema.triggers WHERE trigger_name = '{trigger_name}'", ())

    # endregion

    # region Column Definition with Generated Columns
    def format_column_definition(self, col_def) -> tuple:
        """Format a column definition including generated columns."""
        from rhosocial.activerecord.backend.expression.statements import ColumnConstraintType, GeneratedColumnType
        from rhosocial.activerecord.backend.expression import bases

        all_params = []

        col_sql = f"{self.format_identifier(col_def.name)} {col_def.data_type}"

        for constraint in col_def.constraints:
            if constraint.constraint_type == ColumnConstraintType.PRIMARY_KEY:
                col_sql += " PRIMARY KEY"
            elif constraint.constraint_type == ColumnConstraintType.NOT_NULL:
                col_sql += " NOT NULL"
            elif constraint.constraint_type == ColumnConstraintType.NULL:
                col_sql += " NULL"
            elif constraint.constraint_type == ColumnConstraintType.UNIQUE:
                col_sql += " UNIQUE"
            elif constraint.constraint_type == ColumnConstraintType.DEFAULT:
                if constraint.default_value is None:
                    raise ValueError("DEFAULT constraint must have a default value specified.")
                if isinstance(constraint.default_value, bases.BaseExpression):
                    default_sql, default_params = constraint.default_value.to_sql()
                    col_sql += f" DEFAULT {default_sql}"
                    all_params.extend(default_params)
                else:
                    col_sql += f" DEFAULT {self.get_parameter_placeholder()}"
                    all_params.append(constraint.default_value)
            elif constraint.constraint_type == ColumnConstraintType.CHECK:
                if constraint.check_condition is None:
                    raise ValueError("CHECK constraint must have a check condition specified.")
                check_sql, check_params = constraint.check_condition.to_sql()
                col_sql += f" CHECK ({check_sql})"
                all_params.extend(check_params)
            elif constraint.constraint_type == ColumnConstraintType.FOREIGN_KEY:
                if constraint.foreign_key_reference is None:
                    raise ValueError("FOREIGN KEY constraint must have a foreign key reference specified.")
                ref_table, ref_cols = constraint.foreign_key_reference
                ref_cols_str = ", ".join(self.format_identifier(col) for col in ref_cols)
                col_sql += f" REFERENCES {self.format_identifier(ref_table)}({ref_cols_str})"

        if col_def.generated_expression is not None:
            gen_sql, gen_params = col_def.generated_expression.to_sql()
            all_params.extend(gen_params)

            col_sql += f" GENERATED ALWAYS AS ({gen_sql})"
            if col_def.generated_type == GeneratedColumnType.STORED:
                col_sql += " STORED"
            else:
                col_sql += " VIRTUAL"

        # Add comment if present
        if col_def.comment:
            col_sql += f" COMMENT '{col_def.comment}'"

        return col_sql, tuple(all_params)

    # endregion
