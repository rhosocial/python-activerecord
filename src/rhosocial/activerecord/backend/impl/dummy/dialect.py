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

from rhosocial.activerecord.backend.dialect.mixins import (
    RelationSourceMixin,
    NamespaceMixin,
    TableObjectMixin,
    ViewObjectMixin,
    MaterializedViewObjectMixin,
    ForeignTableObjectMixin,
    IndexObjectMixin,
    SequenceObjectMixin,
    TriggerObjectMixin,
    RoutineObjectMixin,
    TypeObjectMixin,
    SynonymObjectMixin,
    SchemaNameMixin,
    DatabaseNameMixin,
    PropertyGraphNameMixin,
    SQLXMLMixin,
    SQLXMLParsingMixin,
    SQLXMLSerializationMixin,
    SQLXMLConstructionMixin,
    SQLXMLAggregationMixin,
    SQLXMLQueryingMixin,
    CollationMixin,
    WindowFunctionMixin,
    CTEMixin,
    UpsertMixin,
    LateralJoinMixin,
    ArrayMixin,
    JSONMixin,
    UUIDMixin,
    ExplainMixin,
    MergeMixin,
    TemporalTableMixin,
    PivotMixin,
    GraphMixin,
    GraphTableMixin,
    JoinMixin,
    SetOperationMixin,
    ILIKEMixin,
    # DDL Mixins
    TableMixin,
    PartitionMixin,
    ConstraintMixin,
    CommentMixin,
    ViewMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TriggerMixin,
    FunctionMixin,
    GeneratedColumnMixin,
    AutoIncrementColumnMixin,
    IdentityColumnMixin,
    DatabaseMixin,
    # Introspection Mixin
    IntrospectionMixin,
    AsyncIntrospectionMixin,
    AsyncIntrospectionMixin,
    # New Mixins
    PredicateMixin,
    TrimMixin,
    LpadMixin,
    RepeatMixin,
    RpadMixin,
    ExpressionMixin,
    DateTimeMixin,
    DQLMixin,
    DMLMixin,
    DDLColumnMixin,
    ColumnAttributeMixin,
    AlterTableModifierMixin,
    DataTypeMixin,
    UserDefinedTypeMixin,
    DomainMixin,
    TransactionControlMixin,
)
from .column_type import DummyColumnTypeMixin
from .data_type_suggestions import DummyDataTypeSuggestionsMixin
from .index_suggestion import DummyIndexSuggestionMixin
from .general_suggestions import (DummyCreateTableLayoutSuggestionMixin, DummyJSONSuggestionMixin,
    DummyStringConcatenationSuggestionMixin, DummyUpsertSuggestionMixin)
from .expression import _DummyTypeAlterAction, _DummyTypeDefinition
from rhosocial.activerecord.backend.expression.statements.ddl_type import (
    TypeAlterAction,
    TypeDefinition,
)
from rhosocial.activerecord.backend.expression.types import (
    ArrayType, BigIntType, BinaryType, BlobType, BooleanType, CharType, CustomType,
    DateType, DateTimeType, DecimalType, DoubleType, EnumType, FloatType,
    IntegerType, IntervalType, JsonBType, JsonType,
    RealType, SmallIntType, TextType, TimeType, TimeTzType,
    TimestampType, TimestampTzType, TinyIntType, UUIDType, VarBinaryType, VarCharType, XmlType,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.textscan import is_identifier
from typing import Tuple, Type, TYPE_CHECKING

from rhosocial.activerecord.backend.suggestion.definitions import FunctionSuggestion


# ---------------------------------------------------------------------------

#: One precision group, digits only, wherever it appears in the name: the
#: standard writes it before the zone suffix (``TIMESTAMP(3) WITH TIME ZONE``)
#: as well as at the end (``DECIMAL(10,2)``).
#: A trailing array marker, one per dimension.


if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.collation import CollateFunction
    from rhosocial.activerecord.backend.expression.statements import ColumnDefinition
    from rhosocial.activerecord.backend.expression.transaction import (
        BeginTransactionStatement,
        CommitStatement,
        ReleaseSavepointStatement,
        RollbackStatement,
        SavepointStatement,
        SetTransactionStatement,
    )


class DummyDialect(
    # The bases below come in bundles: a backend mixin, then the core bundle
    # it stands in for. The backend's answer has to come first -- a mixin
    # placed after the class it overrides never wins -- so a new mixin goes
    # immediately before the core mixin it overrides, and the pairing is read
    # off the list. Two positions sit outside that pairing and are called out
    # where they occur: a mixin that overrides a method ``SQLDialectBase``
    # defines has to precede the base, and a mixin that subclasses a core
    # mixin has to precede it too (C3: a subclass precedes its base).
    SQLDialectBase,
    RelationSourceMixin,
    # The object tree: each *NameMixin renders one object kind and inherits
    # NamespaceMixin for the namespace levels, so they precede it. The object
    # protocols name the format_*_object methods and inherit NamespaceSupport,
    # so they precede it too. Both groups sit ahead of the DDL mixins because
    # naming an object and changing one are independent capabilities.
    TableObjectMixin,
    ViewObjectMixin,
    MaterializedViewObjectMixin,
    ForeignTableObjectMixin,
    IndexObjectMixin,
    SequenceObjectMixin,
    TriggerObjectMixin,
    RoutineObjectMixin,
    TypeObjectMixin,
    SynonymObjectMixin,
    SchemaNameMixin,
    DatabaseNameMixin,
    PropertyGraphNameMixin,
    NamespaceMixin,
    # One protocol per DDL statement expression.
    SQLXMLMixin,
    SQLXMLParsingMixin,
    SQLXMLSerializationMixin,
    SQLXMLConstructionMixin,
    SQLXMLAggregationMixin,
    SQLXMLQueryingMixin,
    CollationMixin,
    WindowFunctionMixin,
    CTEMixin,
    UpsertMixin,
    LateralJoinMixin,
    ArrayMixin,
    JSONMixin,
    UUIDMixin,
    ExplainMixin,
    MergeMixin,
    TemporalTableMixin,
    PivotMixin,
    GraphMixin,
    GraphTableMixin,
    JoinMixin,
    SetOperationMixin,
    ILIKEMixin,
    # DDL Mixins
    TableMixin,
    PartitionMixin,
    ConstraintMixin,
    CommentMixin,
    ViewMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TriggerMixin,
    FunctionMixin,
    GeneratedColumnMixin,
    AutoIncrementColumnMixin,
    IdentityColumnMixin,
    DatabaseMixin,
    # Introspection Mixin
    IntrospectionMixin,
    AsyncIntrospectionMixin,
    # New Mixins
    PredicateMixin,
    TrimMixin,
    LpadMixin,
    RepeatMixin,
    RpadMixin,
    ExpressionMixin,
    DateTimeMixin,
    DQLMixin,
    DMLMixin,
    # Value literals: the typed value nodes render through this, and the Dummy
    # dialect has no backend-specific spelling to add on top of it.
    # Suggested data types: the DDL half of the same answer, installed ahead of
    # the mixin that withholds the table.
    DummyDataTypeSuggestionsMixin,
    DummyCreateTableLayoutSuggestionMixin,
    DummyIndexSuggestionMixin,
    DummyJSONSuggestionMixin,
    DummyUpsertSuggestionMixin,
    DummyStringConcatenationSuggestionMixin,
    DataTypeMixin,
    DummyColumnTypeMixin,
    UserDefinedTypeMixin,
    DomainMixin,
    DDLColumnMixin,
    ColumnAttributeMixin,
    AlterTableModifierMixin,
    TransactionControlMixin,
    # Protocols for type checking
    # DDL Protocols
    # Introspection Protocols
    # Transaction Control Protocol
    # DDL statement protocols follow the DDL mixins: a protocol's empty
    # body would otherwise win over the mixin that actually renders.
):
    """
    Dummy dialect supporting all features for SQL generation testing.
    """

    def __init__(self) -> None:
        """Initialize dummy dialect with a placeholder version."""
        from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
        SQLDialectBase.__init__(self)
        # Set a default version since dummy doesn't represent a real database
        self._version = (1, 0, 0)

    def artifact_registry(self):
        """The kinds this backend can read: core's kinds plus the dummy nodes.

        The dummy backend owns its expression module, so the composition lives
        here rather than in core: ``backend_registry()`` is
        ``registry_for_packages("...impl.dummy.expression", base=core_registry())``,
        frozen and cached.
        """
        from .registry import backend_registry

        return backend_registry()

    # ------------------------------------------------------------------
    # DataType formatters (core types — for to_sql() testing)
    # ------------------------------------------------------------------

    def _refuse_unsigned(self, data_type, word: str) -> None:
        """Refuse ``unsigned=True``, because the standard grammar dummy renders
        has no ``UNSIGNED`` attribute.

        Signedness is a **field** on every numeric concept — the four integer
        widths and the three ``DECIMAL`` / ``FLOAT`` / ``DOUBLE`` concepts — so
        ``DecimalType(unsigned=True)`` is constructible and the flag reaches the
        formatter.  Dummy renders the SQL-standard type names, and the standard
        has no ``UNSIGNED``:

        * MySQL's own manual calls the attribute *nonstandard*: "All integer
          types can have an optional (nonstandard) UNSIGNED attribute."
          https://dev.mysql.com/doc/refman/9.7/en/numeric-type-attributes.html
        * PostgreSQL, which does conform, has nothing to place after a type name:
          its numeric-types chapter enumerates each integer with one symmetric
          range and no unsigned variant anywhere in it.
          https://www.postgresql.org/docs/current/datatype-numeric.html

        So there is not even a spelling that would parse.  Writing bare
        ``DECIMAL`` or ``INTEGER`` for an unsigned request would create a column
        that accepts the negatives the caller declared it would not, and report
        success: the same silent loss as accepting the flag and discarding it,
        which is what this replaces.

        The guard lives here, at the rendering end, rather than in the
        expression's constructor: an expression collects ``unsigned`` without
        judging it, because only the formatter knows which backend will have to
        honour it. A non-boolean therefore reaches this point instead of being
        rejected at construction, and is named here -- silently dropping it
        would render a signed column for a caller who asked for an unsigned one,
        which is the failure this whole refusal exists to prevent.

        ``word`` is the concept the caller asked for, so the message can say
        *which* type was refused.  ``UnsupportedFeatureError``, not
        ``ValueError``: the declaration is not a wrong value, it is a
        declaration this grammar cannot express at all, and the two exceptions
        do not share a base class.
        """
        unsigned = data_type.unsigned
        if not isinstance(unsigned, bool):
            raise TypeError(
                f"unsigned must be a bool, got {type(unsigned).__name__}; it "
                f"becomes a type modifier in the rendered DDL."
            )
        if not unsigned:
            return
        raise UnsupportedFeatureError(
            self.name,
            f"an unsigned {word} column "
            f"(dummy renders the SQL-standard type names, and the standard has "
            f"no UNSIGNED attribute to place after a type name; MySQL calls its "
            f"own UNSIGNED nonstandard, and PostgreSQL's numeric-types chapter "
            f"lists no unsigned variant)",
            suggestion=(
                "Declare the column signed and enforce the range with a CHECK "
                "constraint if negatives must be rejected."
            ),
        )

    def format_data_type_tinyint(self, expr: TinyIntType) -> "Tuple[str, tuple]":
        self._refuse_unsigned(expr, "TINYINT")
        return "TINYINT", ()

    def format_data_type_smallint(self, expr: SmallIntType) -> "Tuple[str, tuple]":
        self._refuse_unsigned(expr, "SMALLINT")
        return "SMALLINT", ()

    def format_data_type_integer(self, expr: IntegerType) -> "Tuple[str, tuple]":
        """The dummy dialect renders every spelling of this one type verbatim,
        which is what makes it useful for testing dispatch.

        ``unsigned`` is refused rather than ignored; see
        :meth:`_refuse_unsigned`."""
        if expr.spelling not in IntegerType.SPELLINGS:
            raise TypeError(
                f"{type(self).__name__} cannot render {expr.spelling!r}; "
                f"it accepts {', '.join(IntegerType.SPELLINGS)}."
            )
        self._refuse_unsigned(expr, "INTEGER")
        return "INT" if expr.spelling == "int" else "INTEGER", ()

    def format_data_type_bigint(self, expr: BigIntType) -> "Tuple[str, tuple]":
        self._refuse_unsigned(expr, "BIGINT")
        return "BIGINT", ()

    def format_data_type_real(self, expr: RealType) -> "Tuple[str, tuple]":
        # REAL is refused for unsigned for the same reason as every other
        # numeric here: the grammar this dialect renders has no UNSIGNED
        # modifier, so the flag cannot be honoured and must not be dropped.
        self._refuse_unsigned(expr, "REAL")
        return "REAL", ()

    def format_data_type_double(self, expr: DoubleType) -> "Tuple[str, tuple]":
        self._refuse_unsigned(expr, "DOUBLE PRECISION")
        return "DOUBLE PRECISION", ()

    def format_data_type_text(self, expr: TextType) -> "Tuple[str, tuple]":
        return "TEXT", ()

    def format_data_type_boolean(self, expr: BooleanType) -> "Tuple[str, tuple]":
        return "BOOLEAN", ()

    def format_data_type_blob(self, expr: BlobType) -> "Tuple[str, tuple]":
        return "BLOB", ()

    def format_data_type_date(self, expr: DateType) -> "Tuple[str, tuple]":
        return "DATE", ()

    def format_data_type_json(self, expr: JsonType) -> "Tuple[str, tuple]":
        return "JSON", ()

    def format_data_type_jsonb(self, expr: JsonBType) -> "Tuple[str, tuple]":
        return "JSONB", ()

    def format_data_type_xml(self, expr: XmlType) -> "Tuple[str, tuple]":
        return "XML", ()

    def format_data_type_uuid(self, expr: UUIDType) -> "Tuple[str, tuple]":
        return "UUID", ()

    def format_data_type_char(self, expr: CharType) -> "Tuple[str, tuple]":
        return (f"CHAR({expr.length})" if expr.length is not None else "CHAR"), ()

    def format_data_type_varchar(self, expr: VarCharType) -> "Tuple[str, tuple]":
        return (f"VARCHAR({expr.length})" if expr.length is not None else "VARCHAR"), ()

    def format_data_type_binary(self, expr: BinaryType) -> "Tuple[str, tuple]":
        return (f"BINARY({expr.length})" if expr.length is not None else "BINARY"), ()

    def format_data_type_varbinary(self, expr: VarBinaryType) -> "Tuple[str, tuple]":
        return (f"VARBINARY({expr.length})" if expr.length is not None else "VARBINARY"), ()

    def format_data_type_enum(self, expr: EnumType) -> "Tuple[str, tuple]":
        # format_literal rather than an f-string of quotes: it is the dialect's
        # own escaping, so a value containing a quote survives.
        values = ",".join(self.format_literal(value) for value in expr.values)
        return f"ENUM({values})", ()

    def format_data_type_float(self, expr: FloatType) -> "Tuple[str, tuple]":
        self._refuse_unsigned(expr, "FLOAT")
        return (f"FLOAT({expr.precision})" if expr.precision is not None else "FLOAT"), ()

    def format_data_type_decimal(self, expr: DecimalType) -> "Tuple[str, tuple]":
        self._refuse_unsigned(expr, "DECIMAL")
        if expr.precision is not None and expr.scale is not None:
            return f"DECIMAL({expr.precision},{expr.scale})", ()
        if expr.precision is not None:
            return f"DECIMAL({expr.precision})", ()
        return "DECIMAL", ()

    def format_data_type_time(self, expr: TimeType) -> "Tuple[str, tuple]":
        return (f"TIME({expr.precision})" if expr.precision is not None else "TIME"), ()

    def format_data_type_timetz(self, expr: TimeTzType) -> "Tuple[str, tuple]":
        base = f"TIME({expr.precision})" if expr.precision is not None else "TIME"
        return f"{base} WITH TIME ZONE", ()

    def format_data_type_datetime(self, expr: DateTimeType) -> "Tuple[str, tuple]":
        return (f"DATETIME({expr.precision})" if expr.precision is not None else "DATETIME"), ()

    def format_data_type_timestamp(self, expr: TimestampType) -> "Tuple[str, tuple]":
        return (f"TIMESTAMP({expr.precision})" if expr.precision is not None else "TIMESTAMP"), ()

    def format_data_type_timestamptz(self, expr: TimestampTzType) -> "Tuple[str, tuple]":
        base = f"TIMESTAMP({expr.precision})" if expr.precision is not None else "TIMESTAMP"
        return f"{base} WITH TIME ZONE", ()

    def format_data_type_interval(self, expr: IntervalType) -> "Tuple[str, tuple]":
        return (f"INTERVAL {expr.fields}" if expr.fields else "INTERVAL"), ()

    def format_data_type_custom(self, expr: CustomType) -> "Tuple[str, tuple]":
        return expr.raw, ()

    def format_data_type_array(self, expr: ArrayType) -> "Tuple[str, tuple]":
        element_sql, _ = self.format_data_type(expr.element_type)
        return element_sql + "[]" * expr.dimensions, ()

    def supports_type_objects(self) -> bool:
        return True

    def supports_create_type(self) -> bool:
        return True

    def supports_alter_type(self) -> bool:
        return True

    def supports_drop_type(self) -> bool:
        return True

    def supported_type_definitions(self) -> Tuple[Type[TypeDefinition], ...]:
        return (_DummyTypeDefinition,)

    def supports_create_type_if_not_exists(self) -> bool:
        return True

    def supports_create_type_or_replace(self) -> bool:
        return True

    def supports_alter_type_if_exists(self) -> bool:
        return True

    def supports_drop_type_if_exists(self) -> bool:
        return True

    def supports_multiple_type_alter_actions(self) -> bool:
        return False

    def format_type_definition(self, expr: TypeDefinition) -> "Tuple[str, tuple]":
        if not self.supports_type_objects():
            raise UnsupportedFeatureError(self.name, "TYPE definition")
        if not issubclass(type(expr), self.supported_type_definitions()):
            raise UnsupportedFeatureError(
                self.name,
                f"TYPE definition {expr.definition_kind}",
            )
        if isinstance(expr, _DummyTypeDefinition):
            data_type_sql, data_type_params = expr.data_type.to_sql()
            return f"AS {data_type_sql}", tuple(data_type_params)
        raise UnsupportedFeatureError(
            self.name,
            f"TYPE definition {expr.definition_kind}",
        )

    def format_type_alter_action(self, expr: TypeAlterAction) -> "Tuple[str, tuple]":
        if not self.supports_type_objects() or not self.supports_alter_type():
            raise UnsupportedFeatureError(self.name, "ALTER TYPE action")
        if isinstance(expr, _DummyTypeAlterAction):
            return f"RENAME TO {self.format_identifier(expr.new_name)}", ()
        raise UnsupportedFeatureError(
            self.name,
            f"ALTER TYPE action {expr.action_kind}",
        )


    def supports_domains(self) -> bool:
        return True

    def supports_domain_nullable(self) -> bool:
        return True

    def supports_domain_not_null(self) -> bool:
        return True

    def supports_named_domain_checks(self) -> bool:
        return True

    def supports_multiple_domain_checks(self) -> bool:
        return True

    def supports_domain_collation(self) -> bool:
        return True

    def supports_multiple_domain_alter_actions(self) -> bool:
        return False

    def supports_drop_domain_if_exists(self) -> bool:
        return False

    def supports_drop_domain_cascade(self) -> bool:
        return False

    def supports_drop_domain_restrict(self) -> bool:
        return False

    def supports_unnamed_domain_check_drop(self) -> bool:
        return False

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

    def validate_collation_name(self, expr: "CollateFunction") -> str:
        """Validate a collation name and return its SQL representation.

        Dummy is a generic SQL-generation test dialect, so it validates that
        the collation name is a syntactically valid identifier without binding
        to any concrete database's collation catalog. This mirrors the other
        dialects (e.g. SQLite's regex check) while remaining deliberately
        permissive.
        """
        if not is_identifier(expr.collation_name):
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

    def supports_json_table(self) -> bool:
        return True

    def supports_explain_analyze(self) -> bool:
        return True

    def supports_explain_verbose(self) -> bool:
        return True

    def supports_explain_costs(self) -> bool:
        return True

    def supports_explain_buffers(self) -> bool:
        return True

    def supports_explain_timing(self) -> bool:
        return True

    def supports_explain_settings(self) -> bool:
        return True

    def supports_explain_wal(self) -> bool:
        return True

    def supports_explain_format_text(self) -> bool:
        return True

    def supports_explain_format_json(self) -> bool:
        return True

    def supports_explain_format_xml(self) -> bool:
        return True

    def supports_explain_format_yaml(self) -> bool:
        return True

    def supports_explain_format_tree(self) -> bool:
        return True

    def supports_explain_format_traditional(self) -> bool:
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

    def supports_for_update_nowait(self) -> bool:
        return True

    def supports_for_update(self) -> bool:
        return True

    def supports_for_share(self) -> bool:
        return True

    def supports_for_no_key_update(self) -> bool:
        return True

    def supports_for_key_share(self) -> bool:
        return True

    def supports_lock_in_share_mode(self) -> bool:
        return True

    def supports_pivot(self) -> bool:
        return True

    def supports_unpivot(self) -> bool:
        return True

    def supports_graph_match(self) -> bool:
        return True

    def supports_quantified_path(self) -> bool:
        return True

    def supports_comma_separated_patterns(self) -> bool:
        return True

    def supports_graph_table(self) -> bool:
        return True

    # The generic row-source renderers inherited from RelationSourceMixin are
    # exercised end-to-end, so the two capability probes that default to False
    # (a VALUES row source and a table function) are switched on here. A
    # derived table needs no probe: it is universal SQL.
    def supports_values_table_constructor(self) -> bool:
        return True

    def supports_table_function(self) -> bool:
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

    def supports_ilike(self) -> bool:
        return True

    def supports_offset_without_limit(self) -> bool:
        return True

    def supports_fetch_with_ties(self) -> bool:
        return True

    def supports_nulls_first_last(self) -> bool:
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

    def supports_transactional_ddl(self) -> bool:
        return True

    # The generic TableMixin provides reusable renderings for the CREATE
    # TABLE family (AS / LIKE / CLONE / USING TEMPLATE); Dummy advertises them
    # so the generic implementations are exercised end-to-end.
    def supports_create_table_as(self) -> bool:
        return True

    def supports_create_table_as_bind_parameters(self) -> bool:
        return True

    def supports_create_table_like(self) -> bool:
        return True

    def supports_create_table_clone(self) -> bool:
        return True

    def supports_create_table_using_template(self) -> bool:
        return True

    def supports_create_or_replace_table(self) -> bool:
        return True

    def supports_unlogged_table(self) -> bool:
        return True

    def supports_transient_table(self) -> bool:
        return True

    def supports_table_comment(self) -> bool:
        return True

    def supports_column_comment(self) -> bool:
        """Whether a column-level ``COMMENT 'text'`` attribute is supported.

        DummyDialect renders column comments unconditionally in its
        ``format_column_definition``, so the capability advertises True to
        stay consistent with the actual rendering behavior.
        """
        return True

    def supports_comment_on(self) -> bool:
        """Whether standalone ``COMMENT ON`` statements are supported.

        DummyDialect exercises the generic ``CommentMixin`` rendering path.
        """
        return True

    # Generic partition protocol is exposed through PartitionMixin, but all
    # capabilities stay disabled for dummy because partitioning requires
    # backend-specific storage semantics.

    def supports_table_tablespace(self) -> bool:
        return True

    def supports_table_inheritance(self) -> bool:
        return True

    def supports_drop_column(self) -> bool:
        return True

    def supports_add_column_if_not_exists(self) -> bool:
        return True

    def supports_drop_column_if_exists(self) -> bool:
        return True

    def supports_alter_column_type(self) -> bool:
        return True

    def supports_alter_column_default(self) -> bool:
        return True

    def supports_alter_column_nullability(self) -> bool:
        return True

    def supports_alter_table_index_actions(self) -> bool:
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

    def supports_deferrable_constraint(self) -> bool:
        """Dummy renders every construct the core can express.

        The core default is ``False`` (a SQL:1999 modifier); dummy opts in so
        the deferral render paths stay exercised without a live server.
        """
        return True

    def supports_constraint_enforced(self) -> bool:
        """Dummy renders every construct the core can express.

        The core default is ``False`` (a SQL:2016 modifier); dummy opts in so
        the enforcement render paths stay exercised without a live server.
        """
        return True

    def supports_alter_constraint_enforced(self) -> bool:
        return True

    def supports_validate_constraint(self) -> bool:
        return True

    # endregion

    # region View DDL Support
    def supports_create_view(self) -> bool:
        return True

    def supports_create_view_bind_parameters(self) -> bool:
        return True

    def supports_drop_view(self) -> bool:
        return True

    def supports_or_replace_view(self) -> bool:
        return True

    def supports_create_or_replace_view(self) -> bool:
        return True

    def supports_if_not_exists_view(self) -> bool:
        return True

    def supports_temporary_view(self) -> bool:
        return True

    def supports_materialized_view(self) -> bool:
        return True

    def supports_materialized_view_bind_parameters(self) -> bool:
        return True

    def supports_refresh_materialized_view(self) -> bool:
        return True

    def supports_materialized_view_tablespace(self) -> bool:
        return True

    def supports_materialized_view_storage_options(self) -> bool:
        return True

    def supports_materialized_view_restrict(self) -> bool:
        return True

    def supports_with_data_clause(self) -> bool:
        """Dummy renders the clause on CTAS and materialized views."""
        return True

    def supports_if_exists_view(self) -> bool:
        return True

    def supports_view_check_option(self) -> bool:
        return True

    def supports_cascade_view(self) -> bool:
        return True

    def supports_restrict_view(self) -> bool:
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

    def supports_truncate_restrict(self) -> bool:
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

    def supports_schema_restrict(self) -> bool:
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

    def supports_sequence_start(self) -> bool:
        return True

    def supports_alter_sequence_start(self) -> bool:
        return True

    def supports_sequence_increment(self) -> bool:
        return True

    def supports_sequence_minvalue(self) -> bool:
        return True

    def supports_sequence_maxvalue(self) -> bool:
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

    def supports_trigger_if_exists(self) -> bool:
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

    def supports_drop_function_if_exists(self) -> bool:
        return True

    def supports_drop_function_cascade(self) -> bool:
        return True

    def supports_drop_function_restrict(self) -> bool:
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

    # region Identity / Auto-Increment Column Support
    # Dummy is the reference switchboard, not a product simulation. The
    # generic mixins default every probe to False (fail-closed), so Dummy
    # overrides each to True to exercise both core rendering paths: the
    # SQL-standard GENERATED ... AS IDENTITY clause and the bare
    # AUTO_INCREMENT marker.
    def supports_identity_column(self) -> bool:
        return True

    def supports_identity_generation_always(self) -> bool:
        return True

    def supports_identity_start(self) -> bool:
        return True

    def supports_identity_increment(self) -> bool:
        return True

    def supports_identity_minvalue(self) -> bool:
        return True

    def supports_identity_maxvalue(self) -> bool:
        return True

    def supports_identity_cycle(self) -> bool:
        return True

    def supports_identity_order(self) -> bool:
        return True

    def supports_identity_cache(self) -> bool:
        return True

    def supports_auto_increment_column(self) -> bool:
        return True

    def suggest_generated_value(self, default_type):
        """Decline a generated value (the dummy renders no real DDL).

        ``no-action`` keeps the portable column baseline plain for inferred
        ``Optional[int]`` PKs; an explicitly declared identity still fails
        loudly in the deriver (decision-graph step 5).
        """
        from rhosocial.activerecord.backend.suggestion import GeneratedValueSuggestion

        return GeneratedValueSuggestion(state="no-action")

    def suggest_partition_retention(self, strategy, plan):
        """Decline partition-retention suggestions, keeping the portable baseline plain.

        Dummy implements the protocol but returns the "no action" state; it is
        the safe default, not a real backend answer. Concrete backends override
        with their own retention action chain.
        """
        from rhosocial.activerecord.backend.suggestion import PartitionRetentionSuggestion

        return PartitionRetentionSuggestion(None)

    def suggest_partition_build(self, strategy, plan):
        """Decline partition-build suggestions, keeping the portable baseline plain."""
        from rhosocial.activerecord.backend.suggestion import PartitionBuildSuggestion

        return PartitionBuildSuggestion(None)

    def suggest_partition_add(self, strategy, plan):
        """Decline partition-add suggestions, keeping the portable baseline plain."""
        from rhosocial.activerecord.backend.suggestion import PartitionAddSuggestion

        return PartitionAddSuggestion(None)

    def suggest_partition_drop(self, strategy, plan):
        """Decline partition-drop suggestions, keeping the portable baseline plain."""
        from rhosocial.activerecord.backend.suggestion import PartitionDropSuggestion

        return PartitionDropSuggestion(None)

    def suggest_partition_table_drop(self, strategy, plan):
        """Decline partition table drop suggestions (portable baseline)."""
        from rhosocial.activerecord.backend.suggestion import PartitionTableDropSuggestion

        return PartitionTableDropSuggestion(None)

    def suggest_partition_table_alter(self, strategy, plan):
        """Decline partition table alter suggestions (portable baseline)."""
        from rhosocial.activerecord.backend.suggestion import PartitionTableAlterSuggestion

        return PartitionTableAlterSuggestion(None)

    def suggest_partition_split(self, strategy, plan):
        """Decline partition split suggestions (portable baseline)."""
        from rhosocial.activerecord.backend.suggestion import PartitionSplitSuggestion

        return PartitionSplitSuggestion(None)

    def suggest_partition_merge(self, strategy, plan):
        """Decline partition merge suggestions (portable baseline)."""
        from rhosocial.activerecord.backend.suggestion import PartitionMergeSuggestion

        return PartitionMergeSuggestion(None)

    def supports_database_assigned_integer_column(self) -> bool:
        return True

    # endregion

    # region Database DDL Support
    def supports_database(self) -> bool:
        return True

    def supports_create_database(self) -> bool:
        return True

    def supports_drop_database(self) -> bool:
        return True

    def supports_alter_database(self) -> bool:
        return True

    def supports_database_if_not_exists(self) -> bool:
        return True

    def supports_database_if_exists(self) -> bool:
        return True

    def supports_database_owner(self) -> bool:
        return True

    def supports_database_encoding(self) -> bool:
        return True

    def supports_database_collation(self) -> bool:
        return True

    def supports_database_comment(self) -> bool:
        return True

    def supports_database_tablespace(self) -> bool:
        return True

    def supports_database_template(self) -> bool:
        return True

    def supports_database_connection_limit(self) -> bool:
        return True

    def supports_database_force_drop(self) -> bool:
        return True

    def supports_undrop_database(self) -> bool:
        return True

    def supports_database_or_replace(self) -> bool:
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

    def suggest_functions(self) -> "FunctionSuggestion":
        """Return the SQL function catalogue this dialect renders.

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

        return FunctionSuggestion(result)

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

    def supports_transaction_wait(self) -> bool:
        """Dummy backend supports the WAIT / NO WAIT transaction clause."""
        return True

    def supports_savepoint(self) -> bool:
        """Dummy backend supports savepoints."""
        return True

    def format_begin_transaction_statement(self, expr: "BeginTransactionStatement") -> "Tuple[str, tuple]":
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
        not_deferrable = params.get("not_deferrable")
        if deferrable:
            parts.append("DEFERRABLE")
        elif not_deferrable:
            parts.append("NOT DEFERRABLE")

        wait = params.get("wait")
        no_wait = params.get("no_wait")
        if wait or no_wait:
            if not self.supports_transaction_wait():
                feature = "WAIT" if wait else "NO WAIT"
                raise UnsupportedFeatureError(
                    self.name, f"transaction {feature}",
                    f"{self.name} does not support the {feature} transaction clause.",
                )
            parts.append("WAIT" if wait else "NO WAIT")

        return " ".join(parts), ()

    def format_commit_statement(self, expr: "CommitStatement") -> "Tuple[str, tuple]":
        """Format COMMIT TRANSACTION statement for dummy dialect."""
        return "COMMIT", ()

    def format_rollback_statement(self, expr: "RollbackStatement") -> "Tuple[str, tuple]":
        """Format ROLLBACK TRANSACTION statement for dummy dialect."""
        params = expr.get_params()
        savepoint = params.get("savepoint")
        if savepoint:
            return f"ROLLBACK TO SAVEPOINT {self.format_identifier(savepoint)}", ()
        return "ROLLBACK", ()

    def format_savepoint_statement(self, expr: "SavepointStatement") -> "Tuple[str, tuple]":
        """Format SAVEPOINT statement for dummy dialect."""
        params = expr.get_params()
        name = params.get("name", "")
        return f"SAVEPOINT {self.format_identifier(name)}", ()

    def format_release_savepoint_statement(self, expr: "ReleaseSavepointStatement") -> "Tuple[str, tuple]":
        """Format RELEASE SAVEPOINT statement for dummy dialect."""
        params = expr.get_params()
        name = params.get("name", "")
        return f"RELEASE SAVEPOINT {self.format_identifier(name)}", ()

    def format_set_transaction_statement(self, expr: "SetTransactionStatement") -> "Tuple[str, tuple]":
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
        if deferrable:
            options.append("DEFERRABLE")
        elif params.get("not_deferrable"):
            options.append("NOT DEFERRABLE")

        wait = params.get("wait")
        no_wait = params.get("no_wait")
        if wait or no_wait:
            if not self.supports_transaction_wait():
                feature = "WAIT" if wait else "NO WAIT"
                raise UnsupportedFeatureError(
                    self.name, f"transaction {feature}",
                    f"{self.name} does not support the {feature} transaction clause.",
                )
            options.append("WAIT" if wait else "NO WAIT")

        if options:
            parts.append(" ".join(options))

        return " ".join(parts), ()

    # endregion

    # region Column Definition with Generated Columns
    def format_column_definition(self, expr: "ColumnDefinition") -> "Tuple[str, tuple]":
        """Format a column definition including generated columns.

        Each constraint rides through :meth:`format_column_constraint` -- the
        shared production-level formatter -- so the dummy dialect spells a
        constraint the way every other dialect does and does not keep a second
        implementation of the same grammar here.

        Args:
            expr: Column definition object containing name, data type,
                     constraints, and optional generated column expression.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        all_params: list = []

        col_sql = f"{self.format_identifier(expr.name)} {expr.data_type.to_sql()[0]}"

        for constraint in expr.constraints:
            constraint_sql, constraint_params = self.format_column_constraint(constraint)
            col_sql += constraint_sql
            all_params.extend(constraint_params)

        if expr.generated_expression is not None:
            gen_sql, gen_params = expr.generated_expression.to_sql()
            col_sql += gen_sql
            all_params.extend(gen_params)

        for attr in expr.attributes or ():
            attr_sql, attr_params = self.format_column_attribute(attr)
            col_sql += attr_sql
            all_params.extend(attr_params)

        # Add comment if present (inline column-comment clause).
        if expr.comment is not None:
            comment_sql, comment_params = self.format_column_comment_clause(expr.comment)
            col_sql += comment_sql
            all_params.extend(comment_params)

        return col_sql, tuple(all_params)

    # endregion
