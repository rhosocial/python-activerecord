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

from ..backend.expression.bases import BaseExpression
from ..backend.expression.objects import Index, Table
from ..backend.expression.statements import (
    ColumnCommentClause,
    ColumnConstraint,
    ColumnDefinition,
    ColumnPrimaryKeyConstraint,
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
from .ddl import DDLSource, IdentityAttribute
from .fields import UseSqlType

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
        attributes = [
            attribute
            for attribute in source.column_attributes(field)
            if not isinstance(attribute, IdentityAttribute)
        ]
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
    constraints = list(source.column_constraints(field))
    if not _has_identity(source, field):
        return constraints
    for position, constraint in enumerate(constraints):
        if isinstance(constraint.branch, ColumnPrimaryKeyConstraint):
            constraints[position] = ColumnConstraint(
                dialect,
                branch=ColumnPrimaryKeyConstraint(
                    dialect, is_auto_increment=True
                ),
            )
            return constraints
    raise ValueError(
        f"{source.table_name()}.{field}: an identity declaration needs a "
        "single-column primary key"
    )


def _has_identity(source: DDLSource, field: str) -> bool:
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
    candidates = _declared_types(source, field)
    for candidate in candidates:
        _bind(candidate, dialect)
        try:
            candidate.to_sql()
        except Exception:
            continue
        return candidate
    if not candidates:
        return None
    raise ValueError(
        f"{source.table_name()}.{field}: no declared type is supported by "
        f"{type(dialect).__name__}"
    )


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
