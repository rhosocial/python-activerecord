# src/rhosocial/activerecord/base/derivation.py
"""Turn a DDLSource declaration into statement objects.

This lives on the ActiveRecord side of the boundary: it reads the declaration
surface and builds the generic statement expressions.  It never imports a
concrete backend, and it never decides *policy*: whether indexes or comments
are inlined is the caller's explicit choice.
"""

from __future__ import annotations

import copy
from typing import Any, List, Optional, Sequence, Tuple

from ..backend.dialect.exceptions import (
    UnsupportedDataTypeError,
    UnsupportedFeatureError,
)
from ..backend.suggestion.protocols import IntegerAutoIncrementColumnSuggestionSupport
from ..backend.expression.bases import BaseExpression
from ..backend.expression.objects import Index, Table
from ..backend.expression.statements import (
    ColumnCommentClause,
    ColumnConstraint,
    ColumnDefinition,
    CommentObjectType,
    CommentOnStatement,
    CreateTableOptions,
    CreateTableStatement,
    DropTableStatement,
    IndexDefinition,
)
from ..backend.expression.statements.ddl_index import (
    CreateIndexStatement,
    DropIndexStatement,
)
from ..backend.expression.types import DataType
from .annotation_lookup import describe_annotation, strip_annotation, table_entry_for
from .ddl import DDLSource, IdentityAttribute
from .fields import UseFieldGenerator, UseSqlType

__all__ = [
    "build_create_table_statement",
    "build_drop_table_statement",
    "build_create_index_statements",
    "build_drop_index_statements",
    "build_comment_statements",
]


def build_create_table_statement(
    source: DDLSource,
    dialect: Any,
    *,
    column_order: Optional[Sequence[str]] = None,
    include_indexes: bool = False,
    include_comments: bool = False,
) -> CreateTableStatement:
    """Build a CREATE TABLE statement from *source*.

    A field with no SQL declaration of its own takes the dialect's **suggested**
    storage declaration (``suggest_data_types``), which is a default and
    never overrides a declaration. A single-column integer primary key the
    model says the database generates gets an identity declaration, so the DDL
    agrees with the write path (``required_pk_fields`` asks the caller for
    nothing there).

    ``column_order`` names database columns; it must cover every column
    exactly once (an incomplete list would silently append the rest).
    ``include_indexes`` / ``include_comments`` are explicit policy choices:
    this function never consults dialect capabilities to decide them.
    """
    fields = _ordered_fields(source, column_order)
    columns: List[ColumnDefinition] = []
    for field in fields:
        data_type = _resolve_type(source, field, dialect)
        if data_type is None:
            raise ValueError(
                f"{source.table_name()}.{field} declares no SQL type"
            )
        comment_text = source.column_comment(field)
        comment = (
            ColumnCommentClause(dialect, comment_text)
            if include_comments and comment_text is not None
            else None
        )
        generated = source.generated_column(field)
        generated_expression = (
            generated(dialect) if generated is not None else None
        )
        # A database-generated integer key is the one place the backend's
        # column suggestion is consumed: it supplies both the storage type
        # and the auto-increment mechanism (an expression node the dialect
        # renders). The primary key stays an independent constraint.
        identity = _has_identity(source, field, data_type)
        auto_increment = None
        if identity and isinstance(dialect, IntegerAutoIncrementColumnSuggestionSupport):
            suggestion = dialect.suggest_integer_auto_increment_column(data_type)
            data_type = suggestion.type
            candidate = suggestion.auto_increment
            if isinstance(candidate, BaseExpression):
                auto_increment = candidate

        attributes = [
            attribute
            for attribute in source.column_attributes(field)
            if not isinstance(attribute, IdentityAttribute)
        ]
        if auto_increment is not None:
            attributes.append(auto_increment)
        columns.append(
            ColumnDefinition(
                dialect,
                source.column_name(field),
                data_type,
                constraints=_column_constraints(source, field, data_type, dialect),
                comment=comment,
                generated_expression=generated_expression,
                attributes=attributes,
            )
        )

    indexes: List[IndexDefinition] = []
    if include_indexes:
        indexes = [_inline_index(source, index, dialect) for index in _indexes(source)]

    options = _table_options(source)
    if options is not None:
        options.dialect = dialect
        if not include_comments and options.comment is not None:
            options = copy.copy(options)
            options.dialect = dialect
            options.comment = None

    partition = _table_partition(source)
    if partition is not None:
        partition.dialect = dialect

    return CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, source.table_name()),
        columns=columns,
        indexes=indexes,
        table_constraints=list(source.table_constraints()),
        table_options=options,
        storage_options=source.table_storage_options(),
        partition=partition,
        tablespace=source.table_tablespace(),
        inherits=source.table_inherits(),
    )


def build_drop_table_statement(
    source: DDLSource,
    dialect: Any,
    *,
    if_exists: bool = False,
) -> DropTableStatement:
    return DropTableStatement(
        dialect,
        Table(dialect, source.table_name()),
        if_exists=if_exists,
    )


def build_create_index_statements(
    source: DDLSource,
    dialect: Any,
) -> Tuple[CreateIndexStatement, ...]:
    return tuple(
        _create_index_statement(source, index, dialect)
        for index in _indexes(source)
    )


def build_drop_index_statements(
    source: DDLSource,
    dialect: Any,
    *,
    if_exists: bool = False,
) -> Tuple[DropIndexStatement, ...]:
    return tuple(
        DropIndexStatement(
            dialect,
            index=Index(dialect, index.name),
            table=Table(dialect, source.table_name()),
            if_exists=if_exists,
        )
        for index in _indexes(source)
    )


def build_comment_statements(
    source: DDLSource,
    dialect: Any,
) -> Tuple[CommentOnStatement, ...]:
    statements: List[CommentOnStatement] = []
    options = _table_options(source)
    if options is not None and options.comment is not None:
        statements.append(
            CommentOnStatement(
                dialect,
                CommentObjectType.TABLE,
                Table(dialect, source.table_name()),
                options.comment.comment,
            )
        )
    for field in source.ddl_field_names():
        comment = source.column_comment(field)
        if comment is not None:
            statements.append(
                CommentOnStatement(
                    dialect,
                    CommentObjectType.COLUMN,
                    Table(dialect, source.table_name()),
                    comment,
                    column=source.column_name(field),
                )
            )
    return tuple(statements)


# -- columns ---------------------------------------------------------------


def _ordered_fields(source: DDLSource, column_order: Optional[Sequence[str]]) -> List[str]:
    fields = list(source.ddl_field_names())
    if column_order is None:
        return fields
    by_column = {source.column_name(field): field for field in fields}
    requested = list(column_order)
    unknown = [column for column in requested if column not in by_column]
    if unknown:
        raise ValueError(
            f"{source.table_name()}: column_order names unknown column(s) {unknown!r}"
        )
    missing = [column for column in by_column if column not in requested]
    if missing:
        raise ValueError(
            f"{source.table_name()}: column_order is missing column(s) {missing!r}"
        )
    if len(requested) != len(by_column):
        raise ValueError(
            f"{source.table_name()}: column_order repeats a column"
        )
    return [by_column[column] for column in requested]


def _column_constraints(
    source: DDLSource,
    field: str,
    data_type: DataType,
    dialect: Any,
) -> List[ColumnConstraint]:
    # The auto-increment mechanism is carried by the backend suggestion as a
    # column *attribute*, never by a flag on the primary-key constraint. The
    # primary key here is the plain constraint the model declared.
    return list(source.column_constraints(field))


def _has_identity(source: DDLSource, field: str, data_type: DataType) -> bool:
    """Whether this column's value is generated by the database on INSERT.

    Two routes, both deliberate:

    * ``IdentityAttribute`` is an explicit declaration, kept for models that
      spell the mechanism out.
    * Otherwise the *only* inference is: a single-column primary key whose
      Python type is ``Optional[int]`` and which carries no value-generation
      annotation. That type is the declaration -- no ``pk_auto_generated``
      switch. A required ``int`` key is the application's to supply; so is an
      ``Optional[str]`` key or a composite key. Pure mapping/storage annotations
      (``UseColumn``, ``UseSqlType``, ...) do not cancel the inference; only a
      value-generation annotation would, and none exists in stage A.
    """
    if _has_declared_identity(source, field):
        return True
    if source.is_composite_pk():
        return False
    pk_columns = tuple(source.primary_key_columns())
    if len(pk_columns) != 1 or pk_columns[0] != source.column_name(field):
        return False
    if not source.field_is_optional(field):
        return False
    if source.field_python_type(field) is not int:
        return False
    if _has_value_generation_annotation(source, field):
        return False
    return True


def _has_value_generation_annotation(source: DDLSource, field: str) -> bool:
    """Whether *field* carries an annotation that supplies its value.

    A ``UseFieldGenerator`` declaration is the value-source annotation: the
    generator fills the field in Python before the write, so an ``Optional[int]``
    primary key carrying one is *not* a database identity key. Pure mapping
    annotations (``UseColumn``, ``UseSqlType``, ...) are not value generators.
    """
    return any(
        isinstance(annotation, UseFieldGenerator)
        for annotation in source.column_annotations(field)
    )


def _has_declared_identity(source: DDLSource, field: str) -> bool:
    return any(
        isinstance(attribute, IdentityAttribute)
        for attribute in source.column_attributes(field)
    )


# -- indexes ---------------------------------------------------------------


def _indexes(source: DDLSource) -> List[IndexDefinition]:
    indexes: List[IndexDefinition] = []
    for field in source.ddl_field_names():
        indexes.extend(source.column_indexes(field))
    indexes.extend(source.table_indexes())
    return indexes


def _inline_index(
    source: DDLSource, index: IndexDefinition, dialect: Any
) -> IndexDefinition:
    return IndexDefinition(
        dialect,
        name=index.name,
        columns=[
            column if isinstance(column, str) else _bind(column, dialect)
            for column in index.columns
        ],
        unique=index.unique,
        type=index.type,
        partial_condition=_where(index, dialect),
        include_columns=index.include_columns,
        if_not_exists=index.if_not_exists,
        tablespace=index.tablespace,
        if_exists=index.if_exists,
        concurrent=index.concurrent,
    )


def _create_index_statement(
    source: DDLSource, index: IndexDefinition, dialect: Any
) -> CreateIndexStatement:
    return CreateIndexStatement(
        dialect,
        index=Index(dialect, index.name),
        table=Table(dialect, source.table_name()),
        columns=[
            column if isinstance(column, str) else _bind(column, dialect)
            for column in index.columns
        ],
        unique=index.unique,
        if_not_exists=index.if_not_exists,
        index_type=index.type,
        where=_where(index, dialect),
        include=index.include_columns,
        tablespace=index.tablespace,
        concurrent=bool(index.concurrent),
    )


def _where(index: IndexDefinition, dialect: Any) -> Any:
    where = index.partial_condition
    if callable(where) and not isinstance(where, BaseExpression):
        where = where(dialect)
    if isinstance(where, BaseExpression):
        _bind(where, dialect)
    return where


# -- types / options -------------------------------------------------------


def _declared_types(source: DDLSource, field: str) -> tuple:
    declared = source.column_data_type(field)
    if declared is None:
        return ()
    if isinstance(declared, UseSqlType):
        return tuple(declared.data_types)
    if isinstance(declared, DataType):
        return (declared,)
    return tuple(declared)


def _resolve_type(source: DDLSource, field: str, dialect: Any) -> Optional[DataType]:
    """Pick the first declared candidate this dialect can actually render.

    Each candidate is bound on a **copy**: a ``DataType`` is a value object whose
    dialect is a mutable rendering attribute, and the declaration belongs to the
    model, not to this derivation.  Binding the declared instance would leave the
    model's own type pointing at whichever backend derived it last, which goes
    wrong the moment one model is derived for two backends -- sequentially it is
    merely surprising, concurrently it is a race.

    A field that declares nothing falls back to the dialect's **suggested**
    storage declaration, per Python type.  The suggestion is a default, never a
    replacement: an explicit ``UseSqlType`` is always tried first and a declared
    candidate that no dialect can render is still reported as such.

    Only an *answer* moves on to the next candidate: the dialect has no
    rendering for the concept, or it renders the concept but refuses this
    particular declaration (a precision its server cannot honour, say).  Any
    other exception is a defect in the formatter and is deliberately allowed to
    surface -- swallowing it here would report a bug as "no declared type is
    supported", which reads like a capability and sends the reader after the
    wrong thing.

    The refusals are kept. A backend that cannot render a concept already puts
    its substitute and any loss caveat into the error it raises; discarding
    that text here would turn advice into a bare "unsupported". The caller is
    told why each candidate failed, and can then declare a type the backend
    really renders instead of guessing.
    """
    candidates = _declared_types(source, field)
    if not candidates:
        return _suggested_storage_type(source, field, dialect)

    refusals: List[str] = []
    for candidate in candidates:
        bound = copy.copy(candidate)
        _bind(bound, dialect)
        try:
            bound.to_sql()
        except (UnsupportedDataTypeError, UnsupportedFeatureError) as error:
            refusals.append(f"{candidate!r}: {error}")
            continue
        return bound
    detail = "\n".join(f"  - {refusal}" for refusal in refusals)
    raise ValueError(
        f"{source.table_name()}.{field}: no declared type is supported by "
        f"{type(dialect).__name__}. Each candidate was refused:\n{detail}\n"
        f"Declare a type this backend renders (UseSqlType(...))."
    )


def _suggested_storage_type(
    source: DDLSource, field: str, dialect: Any
) -> DataType:
    """The dialect's suggested declaration for a field that declares none.

    Lookup order matches the column-class tables: the suggested table first,
    resolved through the framework-modelled key list (so a ``Point`` reaches
    the ``Geometry`` entry through the subclass walk), then the backend's own
    vocabulary by exact key.  An answer of ``None`` -- or no answer at all --
    is an error naming the model, the column and the Python type, never a
    silent fallback to text.
    """
    python_type = source.field_python_type(field)
    table = dialect.suggest_data_types().table
    entry = table_entry_for(python_type, table)
    suggested = table.get(entry) if entry is not None else None
    if suggested is None:
        extras = dialect.suggest_extra_data_types().table
        suggested = extras.get(strip_annotation(python_type))
    if suggested is None:
        raise ValueError(
            f"{source.table_name()}.{field} declares no SQL type, and "
            f"{type(dialect).__name__} suggests none for "
            f"{describe_annotation(python_type)}. Declare the field with "
            f"UseSqlType(...), or add this Python type to the dialect's "
            f"suggest_data_types()."
        )
    bound = copy.copy(suggested)
    _bind(bound, dialect)
    try:
        bound.to_sql()
    except (UnsupportedDataTypeError, UnsupportedFeatureError) as error:
        raise ValueError(
            f"{source.table_name()}.{field}: {type(dialect).__name__} suggests "
            f"{suggested!r} for {describe_annotation(python_type)}, but cannot "
            f"render it ({error}). Declare the field with UseSqlType(...)."
        ) from error
    return bound


def _table_options(source: DDLSource) -> Optional[CreateTableOptions]:
    options = source.table_options()
    if isinstance(options, (list, tuple)):
        options = options[0] if options else None
    return options if isinstance(options, CreateTableOptions) else None


def _table_partition(source: DDLSource) -> Any:
    partition = source.table_partition()
    if isinstance(partition, (list, tuple)):
        partition = partition[0] if partition else None
    return partition


def _bind(node: Any, dialect: Any) -> Any:
    if isinstance(node, BaseExpression):
        node.dialect = dialect
    return node


# ---------------------------------------------------------------------------
# Suggestion consumers. A suggestion is a complete decision returned as a
# frozen value; these helpers only gate on protocol support and turn the
# value's expression payload into the list the caller applies. No rendering
# layer lives in backend.suggestion.
# ---------------------------------------------------------------------------

_PARTITION_INTENTS = {
    "build": ("PartitionBuildSuggestionSupport", "suggest_partition_build"),
    "add": ("PartitionAddSuggestionSupport", "suggest_partition_add"),
    "drop": ("PartitionDropSuggestionSupport", "suggest_partition_drop"),
    "retention": ("PartitionRetentionSuggestionSupport", "suggest_partition_retention"),
    "table_drop": ("PartitionTableDropSuggestionSupport", "suggest_partition_table_drop"),
    "table_alter": ("PartitionTableAlterSuggestionSupport", "suggest_partition_table_alter"),
    "split": ("PartitionSplitSuggestionSupport", "suggest_partition_split"),
    "merge": ("PartitionMergeSuggestionSupport", "suggest_partition_merge"),
}


def partition_suggestion_operations(
    dialect: Any, intent: str, strategy: Any, plan: object
) -> Optional[List[Any]]:
    """The ordered expression chain a backend suggests for a partition intent.

    Returns ``None`` when the dialect has no matching suggestion protocol, or
    when the suggestion is a structural "no" (``False``/``None`` operations).
    """
    from ..backend.suggestion import protocols as suggestion_protocols

    try:
        protocol_name, method_name = _PARTITION_INTENTS[intent]
    except KeyError as exc:
        raise ValueError(f"unknown partition suggestion intent: {intent!r}") from exc
    protocol = getattr(suggestion_protocols, protocol_name)
    if not isinstance(dialect, protocol):
        return None
    suggestion = getattr(dialect, method_name)(strategy, plan)
    operations = suggestion.operations
    if isinstance(operations, (list, tuple)):
        return [expr for expr in operations if isinstance(expr, BaseExpression)]
    return None


def integer_auto_increment_parts(dialect: Any, data_type: "DataType") -> tuple:
    """Return ``(storage type, auto-increment attributes)`` for a bare int field."""
    from ..backend.suggestion.protocols import IntegerAutoIncrementColumnSuggestionSupport

    if not isinstance(dialect, IntegerAutoIncrementColumnSuggestionSupport):
        return data_type, []
    suggestion = dialect.suggest_integer_auto_increment_column(data_type)
    attributes = (
        [suggestion.auto_increment]
        if isinstance(suggestion.auto_increment, BaseExpression)
        else []
    )
    return suggestion.type, attributes
