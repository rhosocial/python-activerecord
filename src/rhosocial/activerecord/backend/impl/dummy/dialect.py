# src/rhosocial/activerecord/backend/impl/dummy/dialect.py
"""
Dummy backend SQL dialect implementation.

This dialect implements generic protocols for SQL generation testing.
It is used for to_sql() testing and does not involve actual database connections.
Generic table partitioning capability methods are exposed through the default
PartitionMixin, but remain disabled because dummy does not model real
partitioned storage or backend-specific partition DDL semantics.

Architecture Notes:
===================

The dialect mixins in rhosocial.activerecord.backend.dialect.mixins provide
standard SQL implementations for various features. Each mixin includes:

1. supports_* methods: Return the generic SQL-standard behaviour. Features
   that are not universal across databases default to False; concrete
   dialects override a method ONLY when their actual capability differs
   from the generic implementation (overrides read as a per-backend diff).

2. format_* methods: Provide standard SQL generation for the feature.
   These follow SQL standard syntax and are designed to work with the
   Expression classes in rhosocial.activerecord.backend.expression.

This DummyDialect class serves a specific purpose:

- It inherits broad generic mixins to provide SQL standard coverage
- It overrides supports_* methods to return True for SQL generation features,
  effectively "enabling all switches" for DML/DDL capabilities that dummy can model
- Introspection capabilities are DISABLED (return False) since dummy backend
  does not connect to a real database and cannot introspect anything
- No additional format_* implementations are needed since the mixins
  already provide standard SQL generation

In essence, this file is a "switch board" that combines all mixins and
turns on feature flags for SQL generation (DML/DDL), but not for
introspection (which requires a real database connection).

For concrete database dialects (PostgreSQL, MySQL, etc.), they would:
1. Inherit the same mixins
2. Override supports_* methods based on actual database capabilities
3. Override format_* methods where the database deviates from SQL standard
"""

import re

from typing import Dict, List, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.expression.types import (
    ArrayType, BigIntType, BlobType, BooleanType, CharType, CustomType,
    DateType, DateTimeType, DecimalType, DoubleType, FloatType,
    IntType, IntegerType, IntervalType, JsonBType, JsonType,
    RealType, SmallIntType, TextType, TimeType, TimeTzType,
    TimestampType, TimestampTzType, TinyIntType, VarCharType,
)
from rhosocial.activerecord.backend.dialect.protocols import (
    DDLTypeSupport,
    SQLXMLSupport,
    SQLXMLParsingSupport,
    SQLXMLSerializationSupport,
    SQLXMLConstructionSupport,
    SQLXMLAggregationSupport,
    SQLXMLQueryingSupport,
    CollationSupport,
    WindowFunctionSupport,
    CTESupport,
    WildcardSupport,
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
    GraphTableSupport,
    JoinSupport,
    SetOperationSupport,
    ILIKESupport,
    # DDL Protocols
    TableSupport,
    PartitionSupport,
    AlterTableModifierSupport,
    ConstraintSupport,
    ViewSupport,
    TruncateSupport,
    SchemaSupport,
    IndexSupport,
    SequenceSupport,
    TriggerSupport,
    FunctionSupport,
    GeneratedColumnSupport,
    AutoIncrementSupport,
    # Introspection Protocols
    IntrospectionSupport,
    # Transaction Control Protocol
    TransactionControlSupport,
    # Function Support Protocol
    SQLFunctionSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    SQLXMLMixin,
    SQLXMLParsingMixin,
    SQLXMLSerializationMixin,
    SQLXMLConstructionMixin,
    SQLXMLAggregationMixin,
    SQLXMLQueryingMixin,
    CollationMixin,
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
    GraphTableMixin,
    JoinMixin,
    SetOperationMixin,
    ILIKEMixin,
    # DDL Mixins
    TableMixin,
    PartitionMixin,
    ConstraintMixin,
    ViewMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TriggerMixin,
    FunctionMixin,
    GeneratedColumnMixin,
    AutoIncrementMixin,
    # Introspection Mixin
    IntrospectionMixin,
    # New Mixins
    IdentifierMixin,
    PredicateMixin,
    ExpressionMixin,
    DateTimeMixin,
    DQLMixin,
    DMLMixin,
    DDLColumnMixin,
    DDLTypeMixin,
    TransactionControlMixin,
)

_COLLATION_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.collation import CollateExpression
    from rhosocial.activerecord.backend.expression.statements import ColumnDefinition
    from rhosocial.activerecord.backend.expression.transaction import (
        BeginTransactionExpression,
        CommitTransactionExpression,
        ReleaseSavepointExpression,
        RollbackTransactionExpression,
        SavepointExpression,
        SetTransactionExpression,
    )


class DummyDialect(
    SQLDialectBase,
    SQLXMLMixin,
    SQLXMLParsingMixin,
    SQLXMLSerializationMixin,
    SQLXMLConstructionMixin,
    SQLXMLAggregationMixin,
    SQLXMLQueryingMixin,
    CollationMixin,
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
    GraphTableMixin,
    JoinMixin,
    SetOperationMixin,
    ILIKEMixin,
    # DDL Mixins
    TableMixin,
    PartitionMixin,
    ConstraintMixin,
    ViewMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TriggerMixin,
    FunctionMixin,
    GeneratedColumnMixin,
    AutoIncrementMixin,
    # Introspection Mixin
    IntrospectionMixin,
    # New Mixins
    IdentifierMixin,
    PredicateMixin,
    ExpressionMixin,
    DateTimeMixin,
    DQLMixin,
    DMLMixin,
    DDLTypeMixin,
    DDLTypeSupport,
    DDLColumnMixin,
    TransactionControlMixin,
    # Protocols for type checking
    SQLXMLSupport,
    SQLXMLParsingSupport,
    SQLXMLSerializationSupport,
    SQLXMLConstructionSupport,
    SQLXMLAggregationSupport,
    SQLXMLQueryingSupport,
    CollationSupport,
    WindowFunctionSupport,
    CTESupport,
    WildcardSupport,
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
    GraphTableSupport,
    JoinSupport,
    SetOperationSupport,
    ILIKESupport,
    # DDL Protocols
    TableSupport,
    PartitionSupport,
    AlterTableModifierSupport,
    ConstraintSupport,
    ViewSupport,
    TruncateSupport,
    SchemaSupport,
    IndexSupport,
    SequenceSupport,
    TriggerSupport,
    FunctionSupport,
    GeneratedColumnSupport,
    AutoIncrementSupport,
    # Introspection Protocols
    IntrospectionSupport,
    # Transaction Control Protocol
    TransactionControlSupport,
    # Function Support Protocol
    SQLFunctionSupport,
):
    """
    Dummy dialect supporting all features for SQL generation testing.
    """

    def __init__(self) -> None:
        """Initialize dummy dialect with a placeholder version."""
        super().__init__()
        # Set a default version since dummy doesn't represent a real database
        self._version = (1, 0, 0)

    # ------------------------------------------------------------------
    # DataType formatters (core types — for to_sql() testing)
    # ------------------------------------------------------------------

    @DDLTypeMixin.handles(TinyIntType)
    def format_data_type_tinyint(self, data_type: TinyIntType) -> Tuple[str, tuple]:
        return "TINYINT", ()

    @DDLTypeMixin.handles(SmallIntType)
    def format_data_type_smallint(self, data_type: SmallIntType) -> Tuple[str, tuple]:
        return "SMALLINT", ()

    @DDLTypeMixin.handles(IntType)
    def format_data_type_int(self, data_type: IntType) -> Tuple[str, tuple]:
        return "INT", ()

    @DDLTypeMixin.handles(IntegerType)
    def format_data_type_integer(self, data_type: IntegerType) -> Tuple[str, tuple]:
        return "INTEGER", ()

    @DDLTypeMixin.handles(BigIntType)
    def format_data_type_bigint(self, data_type: BigIntType) -> Tuple[str, tuple]:
        return "BIGINT", ()

    @DDLTypeMixin.handles(RealType)
    def format_data_type_real(self, data_type: RealType) -> Tuple[str, tuple]:
        return "REAL", ()

    @DDLTypeMixin.handles(DoubleType)
    def format_data_type_double(self, data_type: DoubleType) -> Tuple[str, tuple]:
        return "DOUBLE PRECISION", ()

    @DDLTypeMixin.handles(TextType)
    def format_data_type_text(self, data_type: TextType) -> Tuple[str, tuple]:
        return "TEXT", ()

    @DDLTypeMixin.handles(BooleanType)
    def format_data_type_boolean(self, data_type: BooleanType) -> Tuple[str, tuple]:
        return "BOOLEAN", ()

    @DDLTypeMixin.handles(BlobType)
    def format_data_type_blob(self, data_type: BlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    @DDLTypeMixin.handles(DateType)
    def format_data_type_date(self, data_type: DateType) -> Tuple[str, tuple]:
        return "DATE", ()

    @DDLTypeMixin.handles(JsonType)
    def format_data_type_json(self, data_type: JsonType) -> Tuple[str, tuple]:
        return "JSON", ()

    @DDLTypeMixin.handles(JsonBType)
    def format_data_type_jsonb(self, data_type: JsonBType) -> Tuple[str, tuple]:
        return "JSONB", ()

    @DDLTypeMixin.handles(CharType)
    def format_data_type_char(self, data_type: CharType) -> Tuple[str, tuple]:
        return (f"CHAR({data_type.length})" if data_type.length is not None else "CHAR"), ()

    @DDLTypeMixin.handles(VarCharType)
    def format_data_type_varchar(self, data_type: VarCharType) -> Tuple[str, tuple]:
        return (f"VARCHAR({data_type.length})" if data_type.length is not None else "VARCHAR"), ()

    @DDLTypeMixin.handles(FloatType)
    def format_data_type_float(self, data_type: FloatType) -> Tuple[str, tuple]:
        return (f"FLOAT({data_type.precision})" if data_type.precision is not None else "FLOAT"), ()

    @DDLTypeMixin.handles(DecimalType)
    def format_data_type_decimal(self, data_type: DecimalType) -> Tuple[str, tuple]:
        if data_type.precision is not None and data_type.scale is not None:
            return f"DECIMAL({data_type.precision},{data_type.scale})", ()
        if data_type.precision is not None:
            return f"DECIMAL({data_type.precision})", ()
        return "DECIMAL", ()

    @DDLTypeMixin.handles(TimeType)
    def format_data_type_time(self, data_type: TimeType) -> Tuple[str, tuple]:
        return (f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"), ()

    @DDLTypeMixin.handles(TimeTzType)
    def format_data_type_timetz(self, data_type: TimeTzType) -> Tuple[str, tuple]:
        base = f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"
        return f"{base} WITH TIME ZONE", ()

    @DDLTypeMixin.handles(DateTimeType)
    def format_data_type_datetime(self, data_type: DateTimeType) -> Tuple[str, tuple]:
        return (f"DATETIME({data_type.precision})" if data_type.precision is not None else "DATETIME"), ()

    @DDLTypeMixin.handles(TimestampType)
    def format_data_type_timestamp(self, data_type: TimestampType) -> Tuple[str, tuple]:
        return (f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"), ()

    @DDLTypeMixin.handles(TimestampTzType)
    def format_data_type_timestamptz(self, data_type: TimestampTzType) -> Tuple[str, tuple]:
        base = f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"
        return f"{base} WITH TIME ZONE", ()

    @DDLTypeMixin.handles(IntervalType)
    def format_data_type_interval(self, data_type: IntervalType) -> Tuple[str, tuple]:
        return (f"INTERVAL {data_type.fields}" if data_type.fields else "INTERVAL"), ()

    @DDLTypeMixin.handles(CustomType)
    def format_data_type_custom(self, data_type: CustomType) -> Tuple[str, tuple]:
        return data_type.raw, ()

    @DDLTypeMixin.handles(ArrayType)
    def format_data_type_array(self, data_type: ArrayType) -> Tuple[str, tuple]:
        element_sql, _ = self.format_data_type(data_type.element_type)
        return element_sql + "[]" * data_type.dimensions, ()

    def parse_type(self, raw: str) -> CustomType:
        """Parse a raw SQL type string — dummy dialect always returns CustomType."""
        from rhosocial.activerecord.backend.expression.types import CustomType
        return CustomType(raw.strip())

    # region Protocol Support Checks - Core Features
    def supports_xmlparse(self) -> bool:
        return True

    def supports_xmlserialize(self) -> bool:
        return True

    def supports_xmlelement(self) -> bool:
        return True

    def supports_xmlattributes(self) -> bool:
        return True

    def supports_xmlforest(self) -> bool:
        return True

    def supports_xmlconcat(self) -> bool:
        return True

    def supports_xmlcomment(self) -> bool:
        return True

    def supports_xmlpi(self) -> bool:
        return True

    def supports_xmlroot(self) -> bool:
        return True

    def supports_xmlagg(self) -> bool:
        return True

    def supports_xmlquery(self) -> bool:
        return True

    def supports_xmlexists(self) -> bool:
        return True

    def supports_xmltable(self) -> bool:
        return True

    def supports_collate_expression(self) -> bool:
        return True

    def validate_collation_name(self, expr: "CollateExpression") -> str:
        """Validate a collation name and return its SQL representation.

        Dummy is a generic SQL-generation test dialect, so it validates that
        the collation name is a syntactically valid identifier without binding
        to any concrete database's collation catalog. This mirrors the other
        dialects (e.g. SQLite's regex check) while remaining deliberately
        permissive.
        """
        if not _COLLATION_NAME_RE.fullmatch(expr.collation_name):
            raise ValueError(f"Invalid collation name: {expr.collation_name!r}")
        return expr.collation_name

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

    def supports_returning_insert(self) -> bool:
        return True

    def supports_returning_update(self) -> bool:
        return True

    def supports_returning_delete(self) -> bool:
        return True

    def supports_upsert(self) -> bool:
        return True

    def get_upsert_syntax_type(self) -> str:
        return "ON CONFLICT"

    def supports_on_conflict_clause(self) -> bool:
        return True

    def supports_multiple_on_conflict_clauses(self) -> bool:
        return True

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

    def supports_for_update(self) -> bool:
        return True

    def supports_graph_match(self) -> bool:
        return True

    def supports_quantified_path(self) -> bool:
        return True

    def supports_comma_separated_patterns(self) -> bool:
        return True

    def supports_graph_table(self) -> bool:
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

    # Generic partition protocol is exposed through PartitionMixin, but all
    # capabilities stay disabled for dummy because partitioning requires
    # backend-specific storage semantics.

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

    # ConstraintSupport methods inherited from ConstraintMixin (all default to True)

    # PostgreSQL-proprietary constraint features (for full SQL generation testing)
    # These are defined directly since DummyDialect cannot import from postgres package.
    # PostgresConstraintSupport/PostgresConstraintMixin in postgres package
    # define the same methods with identical signatures.
    def supports_constraint_novalidate(self) -> bool:
        """Whether NOT VALID constraint option is supported (PG-proprietary)."""
        return True

    def supports_exclude_constraint(self) -> bool:
        """Whether EXCLUDE constraints are supported (PG-proprietary)."""
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

    # region Introspection Support - DISABLED
    # Dummy backend does not connect to a real database, so introspection
    # capabilities are not available. All supports_* methods return False.

    def supports_introspection(self) -> bool:
        """Dummy backend does not support introspection (no real database)."""
        return False

    def supports_database_info(self) -> bool:
        """Dummy backend does not support database info query."""
        return False

    def supports_table_introspection(self) -> bool:
        """Dummy backend does not support table introspection."""
        return False

    def supports_column_introspection(self) -> bool:
        """Dummy backend does not support column introspection."""
        return False

    def supports_index_introspection(self) -> bool:
        """Dummy backend does not support index introspection."""
        return False

    def supports_foreign_key_introspection(self) -> bool:
        """Dummy backend does not support foreign key introspection."""
        return False

    def supports_view_introspection(self) -> bool:
        """Dummy backend does not support view introspection."""
        return False

    def supports_trigger_introspection(self) -> bool:
        """Dummy backend does not support trigger introspection."""
        return False

    # No format_* methods for introspection - the mixin defaults will raise
    # UnsupportedFeatureError when called, which is the correct behavior.

    # endregion

    # region Transaction Control Support

    def supports_functions(self) -> Dict[str, bool]:
        """Return supported SQL functions as function_name -> bool mapping.

        Dummy dialect includes all core functions from:
        rhosocial.activerecord.backend.expression.functions

        It does NOT include any backend-specific functions (like sqlite or mysql)
        since it represents an abstract/standard SQL dialect.

        Returns:
            Dict mapping function names to True (supported) or False.
        """
        from rhosocial.activerecord.backend.expression.functions import (
            __all__ as core_functions,
        )

        result = {}
        for func_name in core_functions:
            result[func_name] = True

        return result

    def supports_transaction_mode(self) -> bool:
        """Dummy backend supports all transaction modes."""
        return True

    def supports_isolation_level_in_begin(self) -> bool:
        """Dummy backend supports isolation level in BEGIN statement."""
        return True

    def supports_read_only_transaction(self) -> bool:
        """Dummy backend supports READ ONLY transactions."""
        return True

    def supports_deferrable_transaction(self) -> bool:
        """Dummy backend supports DEFERRABLE transactions."""
        return True

    def supports_savepoint(self) -> bool:
        """Dummy backend supports savepoints."""
        return True

    def format_begin_transaction(self, expr: "BeginTransactionExpression") -> Tuple[str, tuple]:
        """Format BEGIN TRANSACTION statement for dummy dialect."""
        params = expr.get_params()
        parts = ["BEGIN"]

        isolation = params.get("isolation_level")
        if isolation:
            level_str = self.get_isolation_level_name(isolation)
            parts.append(f"ISOLATION LEVEL {level_str}")

        mode = params.get("mode")
        if mode:
            mode_name = mode.name if hasattr(mode, "name") else str(mode)
            if mode_name == "READ_ONLY":
                parts.append("READ ONLY")
            elif mode_name == "READ_WRITE":
                parts.append("READ WRITE")

        deferrable = params.get("deferrable")
        if deferrable is not None and isolation:
            isolation_name = isolation.name if hasattr(isolation, "name") else str(isolation)
            if isolation_name == "SERIALIZABLE":
                parts.append("DEFERRABLE" if deferrable else "NOT DEFERRABLE")

        return " ".join(parts), ()

    def format_commit_transaction(self, expr: "CommitTransactionExpression") -> Tuple[str, tuple]:
        """Format COMMIT TRANSACTION statement for dummy dialect."""
        return "COMMIT", ()

    def format_rollback_transaction(self, expr: "RollbackTransactionExpression") -> Tuple[str, tuple]:
        """Format ROLLBACK TRANSACTION statement for dummy dialect."""
        params = expr.get_params()
        savepoint = params.get("savepoint")
        if savepoint:
            return f"ROLLBACK TO SAVEPOINT {self.format_identifier(savepoint)}", ()
        return "ROLLBACK", ()

    def format_savepoint(self, expr: "SavepointExpression") -> Tuple[str, tuple]:
        """Format SAVEPOINT statement for dummy dialect."""
        params = expr.get_params()
        name = params.get("name", "")
        return f"SAVEPOINT {self.format_identifier(name)}", ()

    def format_release_savepoint(self, expr: "ReleaseSavepointExpression") -> Tuple[str, tuple]:
        """Format RELEASE SAVEPOINT statement for dummy dialect."""
        params = expr.get_params()
        name = params.get("name", "")
        return f"RELEASE SAVEPOINT {self.format_identifier(name)}", ()

    def format_set_transaction(self, expr: "SetTransactionExpression") -> Tuple[str, tuple]:
        """Format SET TRANSACTION statement for dummy dialect."""
        params = expr.get_params()
        parts = []

        if params.get("session"):
            parts.append("SET SESSION CHARACTERISTICS AS TRANSACTION")
        else:
            parts.append("SET TRANSACTION")

        options = []

        isolation = params.get("isolation_level")
        if isolation:
            level_str = self.get_isolation_level_name(isolation)
            options.append(f"ISOLATION LEVEL {level_str}")

        mode = params.get("mode")
        if mode:
            mode_name = mode.name if hasattr(mode, "name") else str(mode)
            if mode_name == "READ_ONLY":
                options.append("READ ONLY")
            elif mode_name == "READ_WRITE":
                options.append("READ WRITE")

        deferrable = params.get("deferrable")
        if deferrable is not None:
            options.append("DEFERRABLE" if deferrable else "NOT DEFERRABLE")

        if options:
            parts.append(" ".join(options))

        return " ".join(parts), ()

    # endregion

    # region Column Definition with Generated Columns
    def format_column_definition(self, col_def: "ColumnDefinition") -> Tuple[str, tuple]:
        """Format a column definition including generated columns.

        Args:
            col_def: Column definition object containing name, data type,
                     constraints, and optional generated column expression.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression.statements import (
            ColumnConstraintType,
            GeneratedColumnType,
        )
        from rhosocial.activerecord.backend.expression import bases

        all_params = []

        col_sql = f"{self.format_identifier(col_def.name)} {col_def.data_type.to_sql(self)[0]}"

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
