# src/rhosocial/activerecord/backend/introspection/types.py
"""
Database introspection data structures.

This module defines dataclasses for representing database metadata
in a database-agnostic way, enabling unified introspection across
different database backends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Tuple
from enum import Enum

if TYPE_CHECKING:
    from ..expression.types._base import DataType


class IntrospectionScope(Enum):
    """Introspection scope enumeration."""

    DATABASE = "database"
    SCHEMA = "schema"
    TABLE = "table"
    COLUMN = "column"
    INDEX = "index"
    FOREIGN_KEY = "foreign_key"
    VIEW = "view"
    TRIGGER = "trigger"
    SEQUENCE = "sequence"


class TableType(Enum):
    """Table type enumeration.

    One member per kind a catalog reports, including kinds that behave like an
    ordinary table. A materialized view is refreshed rather than written to,
    and a partitioned table's rows live in its partitions; collapsing either
    into ``BASE_TABLE`` loses the distinction at the only layer that saw it,
    because nothing downstream can recover it.

    Catalog spellings that are vendor-specific rather than standard --
    BigQuery's ``CLONE`` / ``SNAPSHOT``, ClickHouse's engines, Snowflake's
    ``MANAGED`` / ``EVENT`` tables -- stay in ``extra`` beside the member they
    map to, not in this enum.
    """

    BASE_TABLE = "BASE_TABLE"
    VIEW = "VIEW"
    MATERIALIZED_VIEW = "MATERIALIZED_VIEW"
    FOREIGN_TABLE = "FOREIGN_TABLE"
    PARTITIONED_TABLE = "PARTITIONED_TABLE"
    SYSTEM_TABLE = "SYSTEM_TABLE"
    TEMPORARY = "TEMPORARY"
    EXTERNAL = "EXTERNAL"


class ColumnNullable(Enum):
    """Column nullability."""

    NULLABLE = "NULLABLE"
    NOT_NULL = "NOT_NULL"
    UNKNOWN = "UNKNOWN"


class IndexType(Enum):
    """Index type enumeration."""

    BTREE = "BTREE"
    HASH = "HASH"
    GIN = "GIN"
    GIST = "GIST"
    FULLTEXT = "FULLTEXT"
    SPATIAL = "SPATIAL"
    UNKNOWN = "UNKNOWN"


class ReferentialAction(Enum):
    """Foreign key referential action."""

    CASCADE = "CASCADE"
    RESTRICT = "RESTRICT"
    SET_NULL = "SET NULL"
    SET_DEFAULT = "SET DEFAULT"
    NO_ACTION = "NO ACTION"


@dataclass
class IntrospectionDatabaseInfo:
    """Database information."""

    name: str
    version: str
    version_tuple: Tuple[int, int, int]
    vendor: str
    encoding: Optional[str] = None
    collation: Optional[str] = None
    timezone: Optional[str] = None
    size_bytes: Optional[int] = None
    table_count: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexColumnInfo:
    """Index column information."""

    name: str
    ordinal_position: int = 0
    is_descending: bool = False
    is_nulls_first: Optional[bool] = None


@dataclass
class IntrospectionColumnInfo:
    """Column information.

    ``parsed_data_type`` is the column's type as a
    :class:`~...expression.types.DataType` value object, and it is
    :data:`None` for one reason only: **the catalog string could not be
    read.** That is load-bearing rather than incidental, because the schema
    differ branches on it — it compares the two value objects when both sides
    are present, and falls back to comparing the ``data_type`` *strings*
    otherwise.

    So ``None`` means "this backend could not parse this one column", not "this
    column has no type". An introspector therefore must not let one unreadable
    column abort the whole table: degrade that column to ``None`` — which is
    exactly the fallback the differ already takes — and say so with a warning.

    That contract is not theoretical. Turning the field on for the MariaDB
    backend exposed three ``parse_type`` defects that had been invisible while
    it sat permanently ``None``: a ``GEOMETRYCOLLECTION`` column parsing as a
    plain ``GEOMETRY`` (so the differ reported *no* change between a collection
    column and a geometry column), a ``DATETIME(6)`` column parsing with its
    fsp dropped, and a ``UUID`` column parsing to ``CustomType`` although the
    dialect's own formatters write ``UUID``. A field nobody populates cannot
    find anything.
    """

    name: str
    table_name: str
    schema: Optional[str] = None
    ordinal_position: int = 0
    data_type: str = ""
    data_type_full: Optional[str] = None
    parsed_data_type: Optional["DataType"] = None
    nullable: ColumnNullable = ColumnNullable.UNKNOWN
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_unique: bool = False
    is_auto_increment: bool = False
    is_generated: bool = False
    #: The expression a generated column is computed from, when the backend's
    #: catalogue carries it. None means "not read", never "not generated" --
    #: ``is_generated`` answers that. No backend fills this yet: SQLite's
    #: ``PRAGMA table_xinfo`` reports only *that* a column is generated, and the
    #: expression lives in the table's DDL.
    generated_expression: Optional[str] = None
    comment: Optional[str] = None
    character_maximum_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    datetime_precision: Optional[int] = None
    charset: Optional[str] = None
    collation: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexInfo:
    """Index information."""

    name: str
    table_name: str
    schema: Optional[str] = None
    is_unique: bool = False
    is_primary: bool = False
    index_type: IndexType = IndexType.UNKNOWN
    columns: List[IndexColumnInfo] = field(default_factory=list)
    filter_condition: Optional[str] = None
    comment: Optional[str] = None
    size_bytes: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntrospectionForeignKeyInfo:
    """Foreign key information."""

    name: str
    table_name: str
    schema: Optional[str] = None
    columns: List[str] = field(default_factory=list)
    referenced_table: str = ""
    referenced_schema: Optional[str] = None
    referenced_columns: List[str] = field(default_factory=list)
    on_update: ReferentialAction = ReferentialAction.NO_ACTION
    on_delete: ReferentialAction = ReferentialAction.NO_ACTION
    deferrable: Optional[bool] = None
    deferred: Optional[bool] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntrospectionViewInfo:
    """View information."""

    name: str
    schema: Optional[str] = None
    definition: Optional[str] = None
    is_updatable: Optional[bool] = None
    is_insertable: Optional[bool] = None
    check_option: Optional[str] = None
    comment: Optional[str] = None
    columns: List[IntrospectionColumnInfo] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntrospectionTriggerInfo:
    """Trigger information."""

    name: str
    table_name: str
    schema: Optional[str] = None
    timing: str = ""
    events: List[str] = field(default_factory=list)
    level: str = "ROW"
    condition: Optional[str] = None
    definition: Optional[str] = None
    status: str = "ENABLED"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntrospectionTableInfo:
    """Table information.

    The storage slots are the common minimum a cross-dialect consumer needs.
    ``size_bytes`` and ``row_count`` carry the table's total footprint and a
    row estimate; ``data_size_bytes`` and ``index_size_bytes`` carry the split
    for engines whose storage is row-plus-index shaped. An engine whose
    storage is shaped otherwise -- managed byte storage, engine-specific parts
    -- leaves those slots ``None``, which is a legal answer rather than a gap.
    Finer facts (partition-level bytes, billing tiers) belong to the backend's
    own complete class beside this one, not to a wider core type
    (``.claude/rules/introspection.md`` §5).
    """

    name: str
    schema: Optional[str] = None
    table_type: TableType = TableType.BASE_TABLE
    comment: Optional[str] = None
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    data_size_bytes: Optional[int] = None
    index_size_bytes: Optional[int] = None
    auto_increment: Optional[int] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    columns: List[IntrospectionColumnInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    foreign_keys: List[IntrospectionForeignKeyInfo] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SequenceInfo:
    """Common minimum a sequence introspection answer carries.

    ``IntrospectionScope`` named sequences without a result type, so four
    backends grew four incompatible classes. This one is the smallest shape
    every engine with sequences can answer, and the cross-dialect entry
    point: a backend keeps its own complete class -- PostgreSQL's textual
    ``cycle``, MariaDB's sequence type, Oracle's ``order`` and
    ``last_number`` -- with every engine-specific fact as a named field on
    it, joined to this shape by projection rather than by inheritance-wide
    ``extra`` (``.claude/rules/introspection.md`` §5).
    """

    name: str
    schema: Optional[str] = None
    data_type: Optional[str] = None
    start_value: Optional[int] = None
    minimum_value: Optional[int] = None
    maximum_value: Optional[int] = None
    increment: Optional[int] = None
    cycle: Optional[bool] = None
    cache_size: Optional[int] = None
    last_value: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeMetricItem:
    """One runtime measurement, as one narrow row.

    Modelled on :class:`~...status.types.StatusItem` rather than a new shape,
    because the operational families answer the same kind of question -- a
    named number a reader either acts on or does not -- and four parallel
    result types would be four places for the narrow-table rule to drift.

    ``source`` is the one addition that matters: these counters are *since
    something*. The event is per engine (PostgreSQL's statistics reset,
    MySQL's server start, SQL Server's DMV flush), so the number says "how
    much happened in the window the engine remembers" and nothing more. The
    engine states its window in its own subclass beside its own numbers; a
    zero means "nothing in the window", never "nothing ever".
    """

    name: str
    value: Any
    #: What kind of measurement this is, so a consumer can group without
    #: knowing which engine spelled it: ``activity`` for concurrency and
    #: session facts, ``throughput`` for rates and counts, ``latency`` for
    #: timings, ``error`` for failure counts.
    kind: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    #: The reset window this number covers, as the engine names it.
    source: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexUsageStats:
    """How an index is being used, beyond "has it ever been used".

    The common minimum beside :class:`UnusedIndexInfo`: that family answers
    the binary question, this one answers the counters. They are deliberately
    separate answers rather than one type with an ``unused`` flag -- a reader
    asking "is it unused" and a reader asking "how much is it used" want
    different things, and collapsing them forces one of them to compute what
    the other needs.

    ``row_reads`` and ``row_fetches`` are the common slots where the engine
    has them; where it does not they stay ``None``, which is the engine
    saying so rather than reporting a zero it never measured.
    """

    schema: Optional[str] = None
    table_name: str = ""
    index_name: str = ""
    #: Times the planner chose this index, since the statistics were reset.
    scans: Optional[int] = None
    #: Rows read through the index, where the engine counts them.
    rows_read: Optional[int] = None
    #: Rows returned to the client from the index (heap fetches included).
    rows_fetched: Optional[int] = None
    #: Index size in bytes, for the "worth this much space" question.
    size_bytes: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ObjectDependency:
    """One edge of the object dependency graph.

    A dependency is directional and *declared*, not inferred: an engine
    reports what its catalog records as depending on what. ``dependent`` is
    the object that needs ``referenced``, and ``kind`` names the relation in
    the engine's own vocabulary -- a view on a table, an index on a table, a
    function used by a trigger. Dropping an object with dependants fails or
    cascades, so the graph is what answers "what breaks if I drop this".

    ``action`` carries the engine's drop behaviour (CASCADE, RESTRICT, SET
    NULL) where it declares one, because that is the half that decides
    whether the drop is safe.
    """

    schema: Optional[str] = None
    dependent_schema: Optional[str] = None
    #: The object that depends; its type is named in ``dependent_type``.
    dependent: str = ""
    dependent_type: Optional[str] = None
    #: The object depended upon.
    referenced: str = ""
    referenced_type: Optional[str] = None
    #: The relation in the engine's vocabulary.
    kind: Optional[str] = None
    #: What happens to the dependant when the referenced object is dropped.
    action: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DDLStatement:
    """The DDL an engine says recreates an object.

    The answer to "what did this object actually get created as", which no
    amount of structure introspection can reconstruct: a CHECK expression, a
    generated column's expression, a storage parameter and a trigger body all
    live in text only the engine holds.

    ``native`` says whether the text came from the engine's own DDL retrieval
    (``DBMS_METADATA``, ``SHOW CREATE TABLE``) or was assembled by this
    library from catalogue facts. Assembly is a reconstruction and therefore a
    lossy one; a caller deciding whether to trust the text needs to know
    which it is looking at.
    """

    schema: Optional[str] = None
    object_type: Optional[str] = None
    object_name: str = ""
    #: The DDL text, or ``None`` when the engine will not give one.
    ddl: Optional[str] = None
    #: Whether the text is the engine's own or this library's assembly.
    native: Optional[bool] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnusedIndexInfo:
    """An index the engine reports as never having served a query.

    The common minimum is the *address* -- which schema, which table, which
    index -- because that is what every engine that can answer at all will
    answer. Everything about *how* unused it is stays with the backend, and
    the shapes genuinely differ: MySQL's ``sys.schema_unused_indexes`` reports
    an estimated ``rows_searched`` per access, PostgreSQL's
    ``pg_stat_user_indexes`` reports ``idx_scan`` counts that a reader has to
    interpret (zero since the last stats reset, which is not the same as "never
    used ever"). Those facts belong on the backend's own subclass beside this
    one, not as a ``time_window`` or ``confidence`` field guessed at here --
    a field meaning one thing on one engine and another on the next is the bug
    ``extra`` exists to avoid (``.claude/rules/introspection.md`` sec.5).

    Absence of an index from the list is **not** evidence it is used: engines
    report from counters that reset, and MySQL's view only covers indexes it
    can see statistics for. Treat a miss as "no evidence", never as "proof of
    use", and read the backend's own docs for what its numbers cover.
    """

    schema: Optional[str] = None
    table_name: str = ""
    index_name: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TableUsageStats:
    """How a table is being used, as the engine's own counters report it.

    The common minimum is the read/write counter set every engine with a
    statistics collector answers: sequential and indexed reads on one side,
    inserts, updates and deletes on the other. ``estimated_row_count`` rides
    here too because every counter source carries one alongside the counters,
    and a reader needs it to turn a scan count into a share of the table.

    Every counter is **since the statistics were last reset**, and each engine
    resets differently -- PostgreSQL on crash or `pg_stat_reset`, MySQL for as
    long as the server has been up. None of them says "ever". A zero is
    therefore "no access in the window", not "no access", and comparing
    counters across engines is meaningless. The reset semantics are the
    backend's to document beside its own subclass, which carries the
    engine-specific counters (PostgreSQL's dead tuples and last-access times,
    MySQL's read/modified flags) that have no common name.

    Absent slots are ``None`` -- an engine that does not track one of the
    common counters says so rather than reporting a zero it did not measure.
    """

    schema: Optional[str] = None
    table_name: str = ""
    sequential_scans: Optional[int] = None
    indexed_scans: Optional[int] = None
    inserts: Optional[int] = None
    updates: Optional[int] = None
    deletes: Optional[int] = None
    estimated_row_count: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class ProfileSource(str, Enum):
    """Where a data-profile number came from -- and therefore what it means.

    Not a decoration. The same ``null_fraction`` is two different facts
    depending on its origin: PostgreSQL's ``pg_stats.null_frac`` is a *sampled
    estimate* produced by the last ANALYZE, while MySQL's and SQLite's are
    *exact* counts bought with a full aggregate. Reading 0.3 without knowing
    which is which is reading nothing, so the source travels with the number.

    ``str`` because this is a word a JSON artifact carries, not a node in a
    tree -- the same reason ``PartitionStrategy`` is one.
    """

    #: The engine's statistics catalog: cheap, and possibly stale.
    ESTIMATE = "estimate"
    #: Computed here from the rows themselves: exact, and paid for in time.
    AGGREGATE = "aggregate"
    #: Computed over a subset of rows; ``ColumnDataProfile.row_count`` says how
    #: many, and the number is an estimate of the whole.
    SAMPLE = "sample"
    #: The engine answered but did not say how the number was produced.
    UNKNOWN = "unknown"


@dataclass
class ColumnDataProfile:
    """What one column actually holds, as opposed to what it declares.

    The counterpart of :class:`IntrospectionColumnInfo`, which answers what a
    column *promises*. This one answers what the data *is*, and the two
    disagreeing is the most valuable signal either can produce: a ``NOT NULL``
    column holding nulls, a ``TEXT`` column holding nothing but numbers, a
    table declared without a primary key whose every value in one column is
    unique.

    Deliberately *not* here: storage-class distribution, text-format
    fingerprints and unit guesses. The first is a real dialect difference
    (SQLite and ClickHouse carry runtime types; PostgreSQL does not), so it
    belongs on the backend that has it. The other two are interpretations of
    ``min``/``max`` rather than database facts, and building them into a probe
    would mean nine backends writing the same regexes.

    Every slot may be ``None``, and ``None`` means "not measured" rather than
    zero -- an engine that does not keep a figure says so, it does not report
    a zero it never counted.
    """

    schema: Optional[str] = None
    table_name: str = ""
    column_name: str = ""
    #: Fraction of rows holding NULL, in ``[0.0, 1.0]``.
    null_fraction: Optional[float] = None
    #: Distinct non-null values. Some engines estimate this; ``source`` says
    #: how to read it.
    distinct_count: Optional[int] = None
    #: The smallest and largest values, in the driver's own Python types.
    #:
    #: Not strings: for a text column the maximum is the lexicographic one,
    #: for a timestamp it is a datetime, and converting either to text would
    #: force the consumer to parse what it already had. What "smallest" means
    #: depends on the column's declared type, which
    #: :class:`IntrospectionColumnInfo` supplies.
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    #: Rows the profile was computed over -- the whole table for an aggregate,
    #: the sample size for a sample, and the collector's estimate for an
    #: estimate. Beside ``distinct_count`` it is what turns a count into a
    #: share.
    row_count: Optional[int] = None
    #: How the numbers above were produced. See :class:`ProfileSource` -- a
    #: ``str`` Enum, so a consumer writing the engine's own word still gets a
    #: value that compares equal to the member that names it.
    source: Optional[ProfileSource] = None
    #: When the estimate was collected, for sources that can be stale.
    #:
    #: Required reading whenever ``source`` is an estimate: a ``null_fraction``
    #: from seven months ago and one from today are not the same fact, and
    #: without this slot the difference is invisible.
    collected_at: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ColumnValueFrequency:
    """One value a column actually contains, with its weight.

    ``count`` and ``frequency`` are both optional rather than one being
    derived, because engines report one or the other and converting needs a
    row count neither side is obliged to have. A caller holding the row count
    can divide; a library that divided for it would have had to guess.

    ``value`` may be ``None``: a NULL is a legal, and often the most
    interesting, member of a column's value domain.
    """

    value: Optional[Any] = None
    count: Optional[int] = None
    frequency: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JoinCoverage:
    """How much of one column's value domain appears in another's.

    The question a schema-linking consumer asks when no foreign key exists:
    ``orders.customer_ref`` and ``customers.code`` look joinable, but only the
    data can say whether they are.

    Two fractions rather than one because the relation is not symmetric: every
    order's customer may exist while most customers have never ordered. Both
    are estimates, for the reasons :meth:`AbstractIntrospector.estimate_join_coverage`
    records.
    """

    left_schema: Optional[str] = None
    left_table: str = ""
    left_column: str = ""
    right_schema: Optional[str] = None
    right_table: str = ""
    right_column: str = ""
    #: Share of the left column's distinct values that also occur on the right.
    left_coverage: Optional[float] = None
    #: Share of the right column's distinct values that also occur on the left.
    right_coverage: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)
