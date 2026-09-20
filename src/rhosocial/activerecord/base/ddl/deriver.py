# src/rhosocial/activerecord/base/ddl/deriver.py
"""Object-oriented DDL derivation from an ActiveRecord model.

The deriver consumes the model's overridable DDL interfaces
(``column_*(field)`` / ``table_*()``) and turns them into statements. Every
declared candidate passes the three gates: the framework type contract
(:mod:`.contracts`), backend ownership (Gate 1) and dialect renderability
(Gate 2). The dialect is injected at collection time.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .annotations import DDLFieldMetadata
from .contracts import COLUMN_CONTRACTS, TABLE_CONTRACTS
from .selector import DialectExpressionSelector
from .types import ColumnTypeResolutionError, ColumnTypeResolver
from ..fields import UseSqlType
from ...backend.expression.bases import BaseExpression
from ...backend.expression.core import TableExpression
from ...backend.expression.statements.ddl_index import CreateIndexExpression, DropIndexExpression
from ...backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
    DropTableExpression,
    IndexDefinition,
)
from ...backend.expression.types import DataType

if TYPE_CHECKING:  # pragma: no cover
    from ...backend.dialect import SQLDialectBase


class TableDDLDeriver:
    """Derives ``CREATE TABLE`` / ``CREATE INDEX`` / ``DROP TABLE`` for a model."""

    def __init__(self, model: Any, dialect: "SQLDialectBase"):
        self.model = model
        self.dialect = dialect
        self.type_resolver = ColumnTypeResolver(dialect)
        self.selector = DialectExpressionSelector(dialect)
        self.metadata: Dict[str, DDLFieldMetadata] = getattr(model, "__table_ddl_fields__", {}) or {}
        self.pk_columns = tuple(model.primary_key_columns())
        self.composite_pk = model.is_composite_pk()
        # Protocol-guaranteed capability: whether CREATE TABLE accepts inline
        # index definitions (MySQL/MariaDB/ClickHouse dialect convenience).
        self._inline_capable = bool(dialect.supports_inline_index())

    # ----- table-level -----

    def create_table(
        self,
        *,
        if_not_exists: bool = False,
        temporary: bool = False,
        inline_indexes: Optional[bool] = None,
    ) -> CreateTableExpression:
        """Build the ``CREATE TABLE`` expression for the model.

        Args:
            if_not_exists: Add IF NOT EXISTS clause.
            temporary: Build a TEMPORARY table.
            inline_indexes: Whether to carry inline index definitions.
                ``None`` (default) follows the dialect's
                ``supports_inline_index()`` capability; ``True`` forces inline
                indexes (the generic renderer raises UnsupportedFeatureError
                on dialects without inline-index support); ``False`` forces
                standalone CREATE INDEX statements even on inline-capable
                dialects.
        """
        if inline_indexes is None:
            inline = self._inline_capable
        else:
            inline = bool(inline_indexes)
        return CreateTableExpression(
            self.dialect,
            table=self.table_expression(),
            columns=self.columns(),
            indexes=self.indexes() if inline else [],
            table_constraints=self.selector.select(
                TABLE_CONTRACTS["table_constraints"],
                "table_constraints",
                self.model.table_constraints(),
            ),
            table_options=self.selector.select(
                TABLE_CONTRACTS["table_options"], "table_options", self.model.table_options()
            ),
            storage_options=self.selector.select(
                TABLE_CONTRACTS["table_storage_options"],
                "table_storage_options",
                self.model.table_storage_options(),
            ),
            partition=self.selector.select(
                TABLE_CONTRACTS["table_partition"], "table_partition", self.model.table_partition()
            ),
            if_not_exists=if_not_exists,
            temporary=temporary,
        )

    def create_indexes(self) -> List[CreateIndexExpression]:
        """Build standalone ``CREATE INDEX`` statements for indexes that this
        dialect cannot inline into CREATE TABLE.

        On inline-capable dialects (``supports_inline_index()`` is True) all
        indexes ride inside the CREATE TABLE statement, so this returns an
        empty list -- keeping ``create_table()`` + ``create_indexes()`` free of
        overlap (no index is ever created twice).
        """
        if self._inline_capable:
            return []
        return [
            CreateIndexExpression(
                self.dialect,
                index_name=index.name,
                table_name=self.model.table_name(),
                columns=list(index.columns),
                unique=index.unique,
                index_type=index.type,
                where=index.partial_condition,
                include=list(index.include_columns) if index.include_columns else None,
                dialect_options=dict(index.dialect_options or {}),
            )
            for index in self.indexes()
        ]

    def drop_indexes(self) -> List[DropIndexExpression]:
        """Build ``DROP INDEX`` statements for every declared index.

        Unlike :meth:`create_indexes`, this is capability-independent: every
        declared index is dropped with a standalone statement, regardless of
        how it was created (inline or standalone).
        """
        return [
            DropIndexExpression(
                self.dialect,
                index_name=index.name,
                table_name=self.model.table_name(),
            )
            for index in self.indexes()
        ]

    def create_schema(self) -> List[BaseExpression]:
        """The full creation plan: CREATE TABLE followed by any standalone
        CREATE INDEX statements this dialect requires."""
        return [self.create_table(), *self.create_indexes()]

    def drop_schema(self) -> List[BaseExpression]:
        """The full teardown plan: standalone DROP INDEX statements followed
        by DROP TABLE (indexes first, table last)."""
        return [*self.drop_indexes(), self.drop_table()]

    def drop_table(
        self,
        *,
        if_exists: bool = False,
        cascade: Optional[bool] = None,
    ) -> DropTableExpression:
        """Build the ``DROP TABLE`` expression for the model."""
        return DropTableExpression(
            self.dialect,
            table=self.table_expression(),
            if_exists=if_exists,
            cascade=cascade,
        )

    def table_expression(self) -> TableExpression:
        """The (optionally schema-qualified) table reference."""
        return TableExpression(
            self.dialect,
            self.model.table_name(),
            schema_name=self.model.schema_name(),
        )

    def indexes(self) -> List[IndexDefinition]:
        """The model's indexes, bound and filtered through the gates."""
        return self.selector.select(
            TABLE_CONTRACTS["table_indexes"], "table_indexes", self.model.table_indexes()
        )

    # ----- columns -----

    def columns(self) -> List[ColumnDefinition]:
        """Derive every column definition of the table."""
        derived = getattr(self.model, "__derived_fields__", {}) or {}
        return [
            self.column_definition(field)
            for field in self.model.model_fields
            if field not in derived
        ]

    def column_definition(self, field: str) -> ColumnDefinition:
        """Assemble one ``ColumnDefinition`` from the column interfaces."""
        data_type = self.resolve_type(field)
        options = self.selector.select(
            COLUMN_CONTRACTS["column_options"], "column_options", self.model.column_options(field)
        )
        column_cls = (
            options.column_definition_class() if options is not None else ColumnDefinition
        )
        column = column_cls(
            self.dialect,
            self.model.column_name(field),
            data_type,
            constraints=self.column_constraints(field, data_type),
            comment=self.selector.select(
                COLUMN_CONTRACTS["column_comment"], "column_comment", self.model.column_comment(field)
            ),
            generated_expression=self.selector.select(
                COLUMN_CONTRACTS["generated_column"],
                "generated_column",
                self.model.generated_column(field),
            ),
            identity_start=getattr(options, "identity_start", None),
            identity_increment=getattr(options, "identity_increment", None),
        )
        if options is not None:
            options.apply_to(column)
        return column

    def field_metadata(self, field: str) -> DDLFieldMetadata:
        """The DDL metadata for a field, analyzing it on demand if absent."""
        metadata = self.metadata.get(field)
        if metadata is None:
            metadata = DDLFieldMetadata(self.model.model_fields[field])
        return metadata

    def resolve_type(self, field: str) -> DataType:
        """Resolve a field's column type from the declared candidates."""
        metadata = self.field_metadata(field)
        declared = self.model.column_type(field)
        try:
            if declared is None:
                return self.type_resolver.resolve(metadata.python_type)
            if isinstance(declared, UseSqlType):
                return self.type_resolver.resolve(metadata.python_type, declared)
            if isinstance(declared, DataType):
                return self.type_resolver.resolve_candidates(metadata.python_type, [declared])
            return self.type_resolver.resolve_candidates(metadata.python_type, list(declared))
        except ColumnTypeResolutionError as exc:
            raise ColumnTypeResolutionError(f"Field {field!r}: {exc}") from exc

    def column_constraints(self, field: str, data_type: DataType) -> List[ColumnConstraint]:
        """Derive a column's constraints (explicit declarations win over auto)."""
        constraints = self.selector.select(
            COLUMN_CONTRACTS["column_constraints"],
            "column_constraints",
            self.model.column_constraints(field),
        )
        if not self.composite_pk and self.model.column_name(field) in self.pk_columns:
            support = getattr(self.dialect, "supports_auto_increment", None)
            if self.type_resolver.is_integer(data_type) and support is not None and support():
                for constraint in constraints:
                    if constraint.constraint_type == ColumnConstraintType.PRIMARY_KEY:
                        constraint.is_auto_increment = True
        return constraints
