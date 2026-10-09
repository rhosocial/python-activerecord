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

from typing import Dict, List, Tuple, Type, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Literal
from rhosocial.activerecord.backend.expression.types import (
    ArrayType, BigIntType, BinaryType, BlobType, BooleanType, CharType, CustomType,
    DataType, DateType, DateTimeType, DecimalType, DoubleType, EnumType, FloatType,
    IntegerType, IntervalType, JsonBType, JsonType,
    RealType, SmallIntType, TextType, TimeType, TimeTzType,
    TimestampType, TimestampTzType, TinyIntType, UUIDType, VarBinaryType, VarCharType, XmlType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_domain import (
    DomainAlterAction,
    DomainNullability,
)
from rhosocial.activerecord.backend.expression.statements.ddl_type import (
    TypeAlterAction,
    TypeDefinition,
)
from .expression import _DummyTypeAlterAction, _DummyTypeDefinition
from .column_type import DummyColumnTypeMixin
from rhosocial.activerecord.backend.dialect.protocols import (
    # Named-object protocols
    TableObjectSupport,
    ViewObjectSupport,
    MaterializedViewObjectSupport,
    ForeignTableObjectSupport,
    IndexObjectSupport,
    SequenceObjectSupport,
    TriggerObjectSupport,
    RoutineObjectSupport,
    TypeObjectSupport,
    SynonymObjectSupport,
    NamespaceSupport,
    # DDL statement protocols
    DataTypeSupport,
    # Column Class Support Protocol
    ColumnTypeSupport,
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
    UUIDSupport,
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
    PartitionSupport,
    AlterTableModifierSupport,
    ConstraintSupport,
    TruncateSupport,
    CreateSchemaSupport,
    DropSchemaSupport,
    GeneratedColumnSupport,
    AutoIncrementColumnSupport,
    IdentityColumnSupport,
    ColumnAttributeSupport,
    CommentSupport,
    CreateDatabaseSupport,
    DropDatabaseSupport,
    AlterDatabaseSupport,
    # Introspection Protocols
    IntrospectionSupport,
    # Transaction Control Protocol
    TransactionControlSupport,
    # Function Support Protocol
    SQLFunctionSupport,
    # One protocol per DDL statement expression.
    CreateTableSupport,
    CreateTableLikeSupport,
    CreateTableAsSupport,
    CreateTableCloneSupport,
    CreateTableUsingTemplateSupport,
    DropTableSupport,
    AlterTableSupport,
    CreateViewSupport,
    DropViewSupport,
    MaterializedViewSupport,
    CreateIndexSupport,
    DropIndexSupport,
    FulltextIndexSupport,
    CreateSequenceSupport,
    DropSequenceSupport,
    AlterSequenceSupport,
    CreateTriggerSupport,
    DropTriggerSupport,
    CreateRoutineSupport,
    DropRoutineSupport,
    CreateTypeSupport,
    AlterTypeSupport,
    DropTypeSupport,
    CreateDomainSupport,
    AlterDomainSupport,
    DropDomainSupport,
    DateTimeSupport,
    DqlOrderSupport,
    PivotSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    DatabaseNameMixin,
    PropertyGraphNameMixin,
    RelationSourceMixin,
    SchemaNameMixin,
    NamespaceMixin,
    TableNameMixin,
    ViewNameMixin,
    MaterializedViewNameMixin,
    ForeignTableNameMixin,
    IndexNameMixin,
    SequenceNameMixin,
    TriggerNameMixin,
    FunctionNameMixin,
    ProcedureNameMixin,
    TypeNameMixin,
    DomainNameMixin,
    SynonymNameMixin,
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
    CommentOnMixin,
    ViewMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TriggerMixin,
    FunctionMixin,
    GeneratedColumnMixin,
    AutoIncrementMixin,
    IdentityColumnMixin,
    DatabaseMixin,
    # Introspection Mixin
    IntrospectionMixin,
    # New Mixins
    PredicateMixin,
    ExpressionMixin,
    DateTimeMixin,
    DQLMixin,
    DMLMixin,
    DDLColumnMixin,
    DataTypeMixin,
    UserDefinedTypeMixin,
    DomainMixin,
    TransactionControlMixin,
)

_COLLATION_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# ---------------------------------------------------------------------------
# parse_type: the closed vocabulary this dialect can read back
# ---------------------------------------------------------------------------
#
# DummyDialect renders SQL-standard type names (the ``format_data_type_*``
# family on the class below), so those names are exactly what it can parse.
# The point of parsing at all is canonicality: **one concept in, exactly one
# class out, carrying the spelling it was written with**.  ``character varying``
# must come back as the variable-length concept and never as the fixed-length
# one, and ``DOUBLE`` and ``DOUBLE PRECISION`` must come back as the same class
# — the whole reason ``SPELLINGS`` exists is that a second class per synonym
# would make the differ report a change that is not there.
#
# The table is derived from the classes' own ``SPELLINGS`` rather than written
# out, so it cannot drift from the closed list the formatters validate against.

#: The core concepts ``parse_type`` recognises.  ``IntervalType`` is handled
#: before the table lookup because its qualifier is a suffix rather than a name.
#: ``EnumType`` is absent because ``ENUM('a','b')`` is a value list, not a type
#: name — the part that says which values is not the part that says which type,
#: and ``CustomType`` keeps it verbatim.
_PARSE_CONCEPTS = (
    BigIntType, BinaryType, BlobType, BooleanType, CharType, DateTimeType,
    DateType, DecimalType, DoubleType, FloatType, IntegerType, JsonBType,
    JsonType, RealType, SmallIntType, TextType, TimeType, TimeTzType,
    TimestampType, TimestampTzType, TinyIntType, UUIDType, VarBinaryType,
    VarCharType, XmlType,
)

#: ``{UPPER-CASED type name: concept}``.  A concept with several spellings
#: contributes each of them and a concept with one contributes that one, so
#: ``CHAR`` and ``CHARACTER`` land on ``CharType`` while ``CHARACTER VARYING``
#: lands on ``VarCharType`` — three names, two concepts, no ambiguity.
_PARSE_VOCABULARY: Dict[str, Type] = {
    spelling.upper(): concept
    for concept in _PARSE_CONCEPTS
    for spelling in (concept.SPELLINGS or (concept.name,))
}

#: The four names the zoned concepts are *written* as.  Their dispatch names are
#: ``timetz`` / ``timestamptz``, which is what PostgreSQL calls them; the
#: standard spells them out and dummy renders the standard form, so both reach
#: the concept.  ``WITHOUT TIME ZONE`` is the standard's name for the
#: un-suffixed type, so it lands on the un-zoned concept.
_PARSE_VOCABULARY.update({
    "TIME WITH TIME ZONE": TimeTzType,
    "TIMESTAMP WITH TIME ZONE": TimestampTzType,
    "TIME WITHOUT TIME ZONE": TimeType,
    "TIMESTAMP WITHOUT TIME ZONE": TimestampType,
})

#: Which constructor keyword each numeric parameter of a type name fills, in
#: the order the numbers are written.  A concept absent from this table takes no
#: numbers, so ``INT(11)`` is *not* silently read as ``INT`` — a width the type
#: cannot carry is not a type name dummy writes, and it is reported as the raw
#: text instead.
_PARSE_NUMERIC_PARAMS: Dict[Type, Tuple[str, ...]] = {
    BinaryType: ("length",),
    CharType: ("length",),
    DateTimeType: ("precision",),
    DecimalType: ("precision", "scale"),
    FloatType: ("precision",),
    TimeType: ("precision",),
    TimeTzType: ("precision",),
    TimestampType: ("precision",),
    TimestampTzType: ("precision",),
    VarBinaryType: ("length",),
    VarCharType: ("length",),
}

#: One precision group, digits only, wherever it appears in the name: the
#: standard writes it before the zone suffix (``TIMESTAMP(3) WITH TIME ZONE``)
#: as well as at the end (``DECIMAL(10,2)``).
_PARSE_PRECISION_RE = re.compile(r"\(\s*(\d+(?:\s*,\s*\d+)*)?\s*\)")

#: A trailing array marker, one per dimension.
_PARSE_ARRAY_MARKER_RE = re.compile(r"\[\s*\]\s*$")


def _split_precision(raw: str) -> Tuple[str, Tuple[int, ...]]:
    """Split ``TIMESTAMP(3) WITH TIME ZONE`` into its name and its numbers.

    Returns the name with the precision group removed and the numbers as ints,
    in the order they were written.  A name with no precision group comes back
    unchanged with no numbers.
    """
    match = _PARSE_PRECISION_RE.search(raw)
    if match is None:
        return raw, ()
    written = match.group(1) or ""
    numbers = tuple(int(part) for part in written.split(",")) if written.strip() else ()
    return (raw[:match.start()] + raw[match.end():]).strip(), numbers


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
    RelationSourceMixin,
    # The object tree: each *NameMixin renders one object kind and inherits
    # NamespaceMixin for the namespace levels, so they precede it. The object
    # protocols name the format_*_object methods and inherit NamespaceSupport,
    # so they precede it too. Both groups sit ahead of the DDL mixins because
    # naming an object and changing one are independent capabilities.
    TableNameMixin,
    ViewNameMixin,
    MaterializedViewNameMixin,
    ForeignTableNameMixin,
    IndexNameMixin,
    SequenceNameMixin,
    TriggerNameMixin,
    FunctionNameMixin,
    ProcedureNameMixin,
    TypeNameMixin,
    DomainNameMixin,
    SynonymNameMixin,
    SchemaNameMixin,
    DatabaseNameMixin,
    PropertyGraphNameMixin,
    NamespaceMixin,
    TableObjectSupport,
    ViewObjectSupport,
    MaterializedViewObjectSupport,
    ForeignTableObjectSupport,
    IndexObjectSupport,
    SequenceObjectSupport,
    TriggerObjectSupport,
    RoutineObjectSupport,
    TypeObjectSupport,
    SynonymObjectSupport,
    NamespaceSupport,
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
    CommentOnMixin,
    ViewMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TriggerMixin,
    FunctionMixin,
    GeneratedColumnMixin,
    AutoIncrementMixin,
    IdentityColumnMixin,
    DatabaseMixin,
    # Introspection Mixin
    IntrospectionMixin,
    # New Mixins
    PredicateMixin,
    ExpressionMixin,
    DateTimeMixin,
    DQLMixin,
    DMLMixin,
    DataTypeMixin,
    DummyColumnTypeMixin,
    UserDefinedTypeMixin,
    DomainMixin,
    DataTypeSupport,
    ColumnTypeSupport,
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
    UUIDSupport,
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
    PartitionSupport,
    AlterTableModifierSupport,
    ConstraintSupport,
    TruncateSupport,
    GeneratedColumnSupport,
    AutoIncrementColumnSupport,
    IdentityColumnSupport,
    ColumnAttributeSupport,
    CommentSupport,
    # Introspection Protocols
    IntrospectionSupport,
    # Transaction Control Protocol
    TransactionControlSupport,
    # Function Support Protocol
    SQLFunctionSupport,
    # DDL statement protocols follow the DDL mixins: a protocol's empty
    # body would otherwise win over the mixin that actually renders.
    CreateRoutineSupport,
    DropRoutineSupport,
    PivotSupport,
    CreateTableSupport,
    CreateTableLikeSupport,
    CreateTableAsSupport,
    CreateTableCloneSupport,
    CreateTableUsingTemplateSupport,
    DropTableSupport,
    AlterTableSupport,
    CreateViewSupport,
    DropViewSupport,
    MaterializedViewSupport,
    CreateIndexSupport,
    DropIndexSupport,
    FulltextIndexSupport,
    CreateSequenceSupport,
    DropSequenceSupport,
    AlterSequenceSupport,
    CreateTriggerSupport,
    DropTriggerSupport,
    CreateTypeSupport,
    AlterTypeSupport,
    DropTypeSupport,
    CreateDomainSupport,
    AlterDomainSupport,
    DropDomainSupport,
    DateTimeSupport,
    DqlOrderSupport,
    CreateSchemaSupport,
    DropSchemaSupport,
    CreateDatabaseSupport,
    DropDatabaseSupport,
    AlterDatabaseSupport,
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

        ``word`` is the concept the caller asked for, so the message can say
        *which* type was refused.  ``UnsupportedFeatureError``, not
        ``ValueError``: the declaration is not a wrong value, it is a
        declaration this grammar cannot express at all, and the two exceptions
        do not share a base class.
        """
        if not getattr(data_type, "unsigned", False):
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

    def supports_data_type_tinyint(self) -> bool:
        return True

    def format_data_type_tinyint(self, data_type: TinyIntType) -> Tuple[str, tuple]:
        self._refuse_unsigned(data_type, "TINYINT")
        return "TINYINT", ()

    def supports_data_type_smallint(self) -> bool:
        return True

    def format_data_type_smallint(self, data_type: SmallIntType) -> Tuple[str, tuple]:
        self._refuse_unsigned(data_type, "SMALLINT")
        return "SMALLINT", ()

    def supports_data_type_integer(self) -> bool:
        return True

    def format_data_type_integer(self, data_type: IntegerType) -> Tuple[str, tuple]:
        """The dummy dialect renders every spelling of this one type verbatim,
        which is what makes it useful for testing dispatch.

        ``unsigned`` is refused rather than ignored; see
        :meth:`_refuse_unsigned`."""
        if data_type.spelling not in IntegerType.SPELLINGS:
            raise TypeError(
                f"{type(self).__name__} cannot render {data_type.spelling!r}; "
                f"it accepts {', '.join(IntegerType.SPELLINGS)}."
            )
        self._refuse_unsigned(data_type, "INTEGER")
        return "INT" if data_type.spelling == "int" else "INTEGER", ()

    def supports_data_type_bigint(self) -> bool:
        return True

    def format_data_type_bigint(self, data_type: BigIntType) -> Tuple[str, tuple]:
        self._refuse_unsigned(data_type, "BIGINT")
        return "BIGINT", ()

    def supports_data_type_real(self) -> bool:
        return True

    def format_data_type_real(self, data_type: RealType) -> Tuple[str, tuple]:
        return "REAL", ()

    def supports_data_type_double(self) -> bool:
        return True

    def format_data_type_double(self, data_type: DoubleType) -> Tuple[str, tuple]:
        self._refuse_unsigned(data_type, "DOUBLE PRECISION")
        return "DOUBLE PRECISION", ()

    def supports_data_type_text(self) -> bool:
        return True

    def format_data_type_text(self, data_type: TextType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def supports_data_type_boolean(self) -> bool:
        return True

    def format_data_type_boolean(self, data_type: BooleanType) -> Tuple[str, tuple]:
        return "BOOLEAN", ()

    def supports_data_type_blob(self) -> bool:
        return True

    def format_data_type_blob(self, data_type: BlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    def supports_data_type_date(self) -> bool:
        return True

    def format_data_type_date(self, data_type: DateType) -> Tuple[str, tuple]:
        return "DATE", ()

    def supports_data_type_json(self) -> bool:
        return True

    def format_data_type_json(self, data_type: JsonType) -> Tuple[str, tuple]:
        return "JSON", ()

    def supports_data_type_jsonb(self) -> bool:
        return True

    def format_data_type_jsonb(self, data_type: JsonBType) -> Tuple[str, tuple]:
        return "JSONB", ()

    def supports_data_type_xml(self) -> bool:
        return True

    def format_data_type_xml(self, data_type: XmlType) -> Tuple[str, tuple]:
        return "XML", ()

    def supports_data_type_uuid(self) -> bool:
        return True

    def format_data_type_uuid(self, data_type: UUIDType) -> Tuple[str, tuple]:
        return "UUID", ()

    def supports_data_type_char(self) -> bool:
        return True

    def format_data_type_char(self, data_type: CharType) -> Tuple[str, tuple]:
        return (f"CHAR({data_type.length})" if data_type.length is not None else "CHAR"), ()

    def supports_data_type_varchar(self) -> bool:
        return True

    def format_data_type_varchar(self, data_type: VarCharType) -> Tuple[str, tuple]:
        return (f"VARCHAR({data_type.length})" if data_type.length is not None else "VARCHAR"), ()

    def supports_data_type_binary(self) -> bool:
        return True

    def format_data_type_binary(self, data_type: BinaryType) -> Tuple[str, tuple]:
        return (f"BINARY({data_type.length})" if data_type.length is not None else "BINARY"), ()

    def supports_data_type_varbinary(self) -> bool:
        return True

    def format_data_type_varbinary(self, data_type: VarBinaryType) -> Tuple[str, tuple]:
        return (f"VARBINARY({data_type.length})" if data_type.length is not None else "VARBINARY"), ()

    def supports_data_type_enum(self) -> bool:
        return True

    def format_data_type_enum(self, data_type: EnumType) -> Tuple[str, tuple]:
        # format_literal rather than an f-string of quotes: it is the dialect's
        # own escaping, so a value containing a quote survives.
        values = ",".join(self.format_literal(value) for value in data_type.values)
        return f"ENUM({values})", ()

    def supports_data_type_float(self) -> bool:
        return True

    def format_data_type_float(self, data_type: FloatType) -> Tuple[str, tuple]:
        self._refuse_unsigned(data_type, "FLOAT")
        return (f"FLOAT({data_type.precision})" if data_type.precision is not None else "FLOAT"), ()

    def supports_data_type_decimal(self) -> bool:
        return True

    def format_data_type_decimal(self, data_type: DecimalType) -> Tuple[str, tuple]:
        self._refuse_unsigned(data_type, "DECIMAL")
        if data_type.precision is not None and data_type.scale is not None:
            return f"DECIMAL({data_type.precision},{data_type.scale})", ()
        if data_type.precision is not None:
            return f"DECIMAL({data_type.precision})", ()
        return "DECIMAL", ()

    def supports_data_type_time(self) -> bool:
        return True

    def format_data_type_time(self, data_type: TimeType) -> Tuple[str, tuple]:
        return (f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"), ()

    def supports_data_type_timetz(self) -> bool:
        return True

    def format_data_type_timetz(self, data_type: TimeTzType) -> Tuple[str, tuple]:
        base = f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"
        return f"{base} WITH TIME ZONE", ()

    def supports_data_type_datetime(self) -> bool:
        return True

    def format_data_type_datetime(self, data_type: DateTimeType) -> Tuple[str, tuple]:
        return (f"DATETIME({data_type.precision})" if data_type.precision is not None else "DATETIME"), ()

    def supports_data_type_timestamp(self) -> bool:
        return True

    def format_data_type_timestamp(self, data_type: TimestampType) -> Tuple[str, tuple]:
        return (f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"), ()

    def supports_data_type_timestamptz(self) -> bool:
        return True

    def format_data_type_timestamptz(self, data_type: TimestampTzType) -> Tuple[str, tuple]:
        base = f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"
        return f"{base} WITH TIME ZONE", ()

    def supports_data_type_interval(self) -> bool:
        return True

    def format_data_type_interval(self, data_type: IntervalType) -> Tuple[str, tuple]:
        return (f"INTERVAL {data_type.fields}" if data_type.fields else "INTERVAL"), ()

    def supports_data_type_custom(self) -> bool:
        return True

    def format_data_type_custom(self, data_type: CustomType) -> Tuple[str, tuple]:
        return data_type.raw, ()

    def supports_data_type_array(self) -> bool:
        return True

    def format_data_type_array(self, data_type: ArrayType) -> Tuple[str, tuple]:
        element_sql, _ = self.format_data_type(data_type.element_type)
        return element_sql + "[]" * data_type.dimensions, ()

    def parse_type(self, raw: str) -> DataType:
        """Parse a SQL type name back into the concept it names.

        Dummy renders SQL-standard type names, so those names are exactly what
        it can read back, and the answer is **canonical**: one concept in,
        exactly one class out, carrying the spelling it was written with.

        That last part is what keeps the schema differ honest.
        ``parse_type("character varying")`` is a ``VarCharType`` — the
        variable-length concept — and never a ``CharType``: they are different
        storage, and a parser that conflated them would report a column as
        changed when nothing about it had.  Conversely ``parse_type("DOUBLE")``
        and ``parse_type("DOUBLE PRECISION")`` are the *same* class, because
        they are the same type written two ways.

        A name this dialect does not render comes back as ``CustomType``.  That
        is the honest answer for a type the framework has no class for, and it
        is what lets an introspected schema be written back verbatim; it is
        *not* an answer for a name in the table above, which is why the table
        is checked against every core ``SPELLINGS`` entry by
        ``tests/.../dummy2/test_type_spelling_parse.py``.
        """
        stripped = raw.strip()
        if not stripped:
            return CustomType(self, stripped)

        # Array markers are not part of the element's name: ``VARCHAR(30)[]`` is
        # one-dimensional and ``VARCHAR(30)[][]`` two.
        element_name = stripped
        dimensions = 0
        while True:
            marker = _PARSE_ARRAY_MARKER_RE.search(element_name)
            if marker is None:
                break
            element_name = element_name[:marker.start()]
            dimensions += 1

        name, numbers = _split_precision(element_name)
        upper = name.upper()

        # ``INTERVAL`` carries a qualifier rather than a name, so it is matched
        # as a prefix.  IntervalType validates the qualifier itself.
        if upper == "INTERVAL" or upper.startswith("INTERVAL "):
            element = IntervalType(
                self, fields=name[len("INTERVAL"):].strip() or None,
            )
        else:
            concept = _PARSE_VOCABULARY.get(upper)
            fields = _PARSE_NUMERIC_PARAMS.get(concept, ()) if concept else ()
            if concept is None or len(numbers) > len(fields):
                # Either a name dummy does not render, or numbers the concept
                # cannot carry (``INT(11)``). Both are reported verbatim rather
                # than guessed at.
                element = CustomType(self, stripped)
            else:
                kwargs = dict(zip(fields, numbers))
                if concept.SPELLINGS:
                    kwargs["spelling"] = upper.lower()
                element = concept(self, **kwargs)

        if not dimensions:
            return element
        return ArrayType(
            self, element_type=element, dimensions=dimensions,
        )

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

    def supports_type_alter_action(
        self,
        action_type: Type[TypeAlterAction],
    ) -> bool:
        return action_type is _DummyTypeAlterAction

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

    def format_type_definition(self, expr: TypeDefinition) -> Tuple[str, tuple]:
        if not self.supports_type_objects():
            raise UnsupportedFeatureError(self.name, "TYPE definition")
        if not self.supports_type_definition(type(expr)):
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

    def format_type_alter_action(self, expr: TypeAlterAction) -> Tuple[str, tuple]:
        if not self.supports_type_objects() or not self.supports_alter_type():
            raise UnsupportedFeatureError(self.name, "ALTER TYPE action")
        if not self.supports_type_alter_action(type(expr)):
            raise UnsupportedFeatureError(
                self.name,
                f"ALTER TYPE action {expr.action_kind}",
            )
        if isinstance(expr, _DummyTypeAlterAction):
            return f"RENAME TO {self.format_identifier(expr.new_name)}", ()
        raise UnsupportedFeatureError(
            self.name,
            f"ALTER TYPE action {expr.action_kind}",
        )


    def supports_domains(self) -> bool:
        return True

    def supports_domain_nullability(self, nullability: DomainNullability) -> bool:
        return True

    def supports_named_domain_checks(self) -> bool:
        return True

    def supports_multiple_domain_checks(self) -> bool:
        return True

    def supports_domain_collation(self) -> bool:
        return True

    def supports_alter_domain_action(
        self,
        action_type: Type[DomainAlterAction],
    ) -> bool:
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

    # The generic TableMixin provides reusable renderings for the CREATE
    # TABLE family (AS / LIKE / CLONE / USING TEMPLATE); Dummy advertises them
    # so the generic implementations are exercised end-to-end.
    def supports_create_table_as(self) -> bool:
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

        DummyDialect exercises the generic ``CommentOnMixin`` rendering path.
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

    def supports_alter_column_properties(self) -> bool:
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

    def supports_alter_constraint_enforced(self) -> bool:
        return True

    def supports_validate_constraint(self) -> bool:
        return True

    # endregion

    # region View DDL Support
    def supports_create_view(self) -> bool:
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

    def supports_transaction_wait(self) -> bool:
        """Dummy backend supports the WAIT / NO WAIT transaction clause."""
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
        )
        from rhosocial.activerecord.backend.expression import bases

        all_params = []

        col_sql = f"{self.format_identifier(col_def.name)} {col_def.data_type.to_sql()[0]}"

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
                    if default_params and isinstance(constraint.default_value, Literal):
                        # DDL accepts no bind parameters: inline the literal.
                        default_sql = self.inline_sql_literal(constraint.default_value.value)
                        default_params = ()
                    col_sql += f" DEFAULT {default_sql}"
                    all_params.extend(default_params)
                else:
                    # DDL clauses accept no bind parameters: render inline.
                    col_sql += f" DEFAULT {self.format_literal(constraint.default_value)}"
            elif constraint.constraint_type == ColumnConstraintType.CHECK:
                if constraint.check_condition is None:
                    raise ValueError("CHECK constraint must have a check condition specified.")
                check_sql, check_params = constraint.check_condition.to_sql()
                enforcement = self._format_constraint_enforcement(constraint)
                suffix = f" {enforcement}" if enforcement else ""
                col_sql += f" CHECK ({check_sql}){suffix}"
                all_params.extend(check_params)
            elif constraint.constraint_type == ColumnConstraintType.FOREIGN_KEY:
                if constraint.foreign_key_reference is None:
                    raise ValueError("FOREIGN KEY constraint must have a foreign key reference specified.")
                ref_table, ref_cols = constraint.foreign_key_reference
                ref_cols_str = ", ".join(self.format_identifier(col) for col in ref_cols)
                enforcement = self._format_constraint_enforcement(constraint)
                suffix = f" {enforcement}" if enforcement else ""
                col_sql += f" REFERENCES {ref_table.to_sql()[0]}({ref_cols_str}){suffix}"

        if col_def.generated_expression is not None:
            gen_sql, gen_params = col_def.generated_expression.to_sql()
            col_sql += gen_sql
            all_params.extend(gen_params)

        for attr in getattr(col_def, "attributes", None) or ():
            attr_sql, attr_params = self.format_column_attribute(attr)
            col_sql += attr_sql
            all_params.extend(attr_params)

        # Add comment if present (inline column-comment clause).
        if col_def.comment is not None:
            comment_sql, comment_params = self.format_column_comment_clause(col_def.comment)
            col_sql += comment_sql
            all_params.extend(comment_params)

        return col_sql, tuple(all_params)

    # endregion
