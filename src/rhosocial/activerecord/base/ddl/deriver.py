# src/rhosocial/activerecord/base/ddl/deriver.py
"""Object-oriented DDL derivation from an ActiveRecord model.

The deriver consumes the model's overridable DDL interfaces
(``column_*(field)`` / ``table_*()``) and turns them into statements. Every
declared candidate passes the three gates: the framework type contract
(:mod:`.contracts`), backend ownership (Gate 1) and dialect renderability
(Gate 2). The dialect is injected at collection time.

Statement families (§5.12/§5.13): the deriver composes the candidate classes
(dialect-protocol preferred class + generic fallback, or the model's override),
selects the most fitting one through Gate 1 + Gate 2, and instantiates it as
``selected_class(dialect, **params)`` — fully keyword-based, with no
conversion on the AR side.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type, TYPE_CHECKING

from .annotations import DDLFieldMetadata
from .contracts import COLUMN_CONTRACTS, TABLE_CONTRACTS
from .params import StatementParamSchema
from .selector import DeclarationSelectionError, DialectExpressionSelector, ExpressionOwnership
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

    # ----- statement families (§5.12/§5.13) -----

    def _statement_candidates(self, preferred: Optional[Type[Any]], generic: Type[Any]) -> List[Type[Any]]:
        """The candidate classes of a statement family: the dialect's
        preferred class first (order = priority), the generic form last,
        deduplicated."""
        candidates: List[Type[Any]] = []
        for candidate in ([preferred] if preferred is not None else []) + [generic]:
            if candidate not in candidates:
                candidates.append(candidate)
        return candidates

    def _statement_renderable(self, cls: Type[Any]) -> bool:
        """Gate 2 for statement families: the dialect provides the format
        method the class declares."""
        prop = getattr(cls, "format_method", None)
        fget = getattr(prop, "fget", None)
        if fget is None:
            return False
        try:
            method_name = fget(None)
        except Exception:  # noqa: BLE001 - undeclared getter (NotImplementedError)
            return False
        return hasattr(self.dialect, method_name)

    def select_statement_class(
        self,
        candidates: List[Type[Any]],
        statement: str,
    ) -> Type[Any]:
        """Select the most fitting statement class (Gate 1 + Gate 2, §5.12).

        Foreign-backend candidates are skipped; the first remaining candidate
        whose format method this dialect provides wins. All inapplicable
        raises :class:`DeclarationSelectionError`.
        """
        failures: List[Tuple[str, str, str]] = []
        for cls in candidates:
            if self.selector.ownership.classify(cls) == ExpressionOwnership.FOREIGN:
                failures.append(
                    (cls.__name__, self.selector._owner_label(cls), "owned by a foreign backend")
                )
                continue
            if not self._statement_renderable(cls):
                failures.append(
                    (
                        cls.__name__,
                        self.selector._owner_label(cls),
                        "dialect provides no rendering method for it",
                    )
                )
                continue
            return cls
        raise DeclarationSelectionError(statement, failures)

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
        indexes = self.indexes() if inline else []
        if inline:
            self._gate_inline_statement_options(indexes)
        params: Dict[str, Any] = {
            # Canonical parameters, collected by name (§5.13); values are
            # directly usable expressions (§5.5).
            "table": self.table_expression(),
            "columns": self.columns(),
            "indexes": indexes,
            "table_constraints": self.table_constraints(),
            "table_options": self.table_options(),
            "storage_options": self.storage_options(),
            "partition": self.partition(),
            "temporary": temporary,
            "if_not_exists": if_not_exists,
            "inherits": self.model.table_inherits(),
            "tablespace": self.model.table_tablespace(),
        }
        # Statement-family candidates (§5.12): the dialect protocol's
        # preferred class first, the generic form last — or the model's
        # override of the whole list.
        override = self.model.create_table_statement_classes()
        candidates = (
            self._statement_candidates(
                getattr(self.dialect, "preferred_create_table_statement", lambda: None)(),
                CreateTableExpression,
            )
            if override is None
            else self._normalized_classes(override)
        )
        schema = StatementParamSchema(CreateTableExpression)
        selected = self.select_statement_class(candidates, "create_table")
        return schema.instantiate(selected, self.dialect, params)

    def _normalized_classes(self, override: Any) -> List[Type[Any]]:
        """Normalize "class or list" into a list of candidate classes."""
        if isinstance(override, (list, tuple)):
            return list(override)
        return [override]

    def _gate_inline_statement_options(self, indexes: List[IndexDefinition]) -> None:
        """§5.16: statement-level index options cannot ride the inline path.

        An index carried inside CREATE TABLE has no place for
        ``if_not_exists`` / ``tablespace`` / ``concurrent``; a declared one
        raises instead of being silently dropped. The drop-side ``if_exists``
        is not part of the create path and is not gated here.
        """
        offenders: List[Tuple[str, List[str]]] = []
        for index in indexes:
            declared: List[str] = []
            if index.if_not_exists:
                declared.append("if_not_exists")
            if index.tablespace is not None:
                declared.append("tablespace")
            if index.concurrent:
                declared.append("concurrent")
            if declared:
                offenders.append((index.name, declared))
        if offenders:
            details = "; ".join(f"{name!r}: {', '.join(options)}" for name, options in offenders)
            raise ValueError(
                "create_table(): the inline index path cannot carry "
                f"statement-level options ({details}). Use "
                "create_table(inline_indexes=False) with create_indexes() / "
                "drop_indexes() to emit standalone statements per index."
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
        params_template = {
            "table_name": self.model.table_name(),
        }
        schema = StatementParamSchema(CreateIndexExpression)
        candidates = self._statement_candidates(
            getattr(self.dialect, "preferred_create_index_statement", lambda: None)(),
            CreateIndexExpression,
        )
        selected = self.select_statement_class(candidates, "create_indexes")
        return [
            schema.instantiate(
                selected,
                self.dialect,
                {
                    **params_template,
                    "index_name": index.name,
                    "columns": list(index.columns),
                    "unique": index.unique,
                    "index_type": index.type,
                    "where": index.partial_condition,
                    "include": list(index.include_columns) if index.include_columns else None,
                    # Statement-level options (§5.16): per-index declarations
                    # pass through; render gates apply at the dialect.
                    "if_not_exists": bool(index.if_not_exists),
                    "tablespace": index.tablespace,
                    "concurrent": bool(index.concurrent),
                },
            )
            for index in self.indexes()
        ]

    def drop_indexes(self, *, if_exists: bool = False) -> List[DropIndexExpression]:
        """Build ``DROP INDEX`` statements for every declared index.

        Unlike :meth:`create_indexes`, this is capability-independent: every
        declared index is dropped with a standalone statement, regardless of
        how it was created (inline or standalone).
        """
        schema = StatementParamSchema(DropIndexExpression)
        candidates = self._statement_candidates(
            getattr(self.dialect, "preferred_drop_index_statement", lambda: None)(),
            DropIndexExpression,
        )
        selected = self.select_statement_class(candidates, "drop_indexes")
        return [
            schema.instantiate(
                selected,
                self.dialect,
                {
                    "index_name": index.name,
                    "table_name": self.model.table_name(),
                    # Per-index declaration wins over the entry parameter
                    # (explicit wins, §5.7); entry parameter is the fallback.
                    "if_exists": index.if_exists if index.if_exists is not None else if_exists,
                    "concurrent": bool(index.concurrent),
                },
            )
            for index in self.indexes()
        ]

    def creation_plan(self) -> List[BaseExpression]:
        """The full creation plan: CREATE TABLE followed by any standalone
        CREATE INDEX statements this dialect requires."""
        return [self.create_table(), *self.create_indexes()]

    def teardown_plan(self) -> List[BaseExpression]:
        """The full teardown plan: standalone DROP INDEX statements followed
        by DROP TABLE (indexes first, table last)."""
        return [*self.drop_indexes(if_exists=True), self.drop_table()]

    def drop_table(
        self,
        *,
        if_exists: bool = False,
        cascade: Optional[bool] = None,
    ) -> DropTableExpression:
        """Build the ``DROP TABLE`` expression for the model."""
        schema = StatementParamSchema(DropTableExpression)
        candidates = self._statement_candidates(
            getattr(self.dialect, "preferred_drop_table_statement", lambda: None)(),
            DropTableExpression,
        )
        selected = self.select_statement_class(candidates, "drop_table")
        return schema.instantiate(
            selected,
            self.dialect,
            {
                "table": self.table_expression(),
                "if_exists": if_exists,
                "cascade": cascade,
            },
        )

    def table_expression(self) -> TableExpression:
        """The (optionally schema-qualified) table reference."""
        return TableExpression(
            self.dialect,
            self.model.table_name(),
            schema_name=self.model.schema_name(),
        )

    def indexes(self) -> List[IndexDefinition]:
        """The model's indexes, merged and filtered through the gates (§5.4).

        Field-level declarations (``UseIndex`` annotations, collected through
        :meth:`columns_indexes`) and table-level declarations
        (``table_indexes()``) are merged and deduplicated by index name, then
        gate-filtered (foreign-backend candidates are skipped; an owned or
        generic candidate this dialect cannot render raises).
        """
        merged: Dict[str, IndexDefinition] = {}
        for field, field_indexes in (self.model.columns_indexes() or {}).items():
            if field in (getattr(self.model, "__derived_fields__", {}) or {}):
                continue
            for index in field_indexes:
                merged.setdefault(index.name, index)
        for index in self.model.table_indexes():
            merged.setdefault(index.name, index)
        return self.selector.select(
            TABLE_CONTRACTS["table_indexes"], "table_indexes", list(merged.values())
        )

    def table_constraints(self) -> List[Any]:
        """The model's table-level constraints, gate-filtered (§5.4)."""
        return self.selector.select(
            TABLE_CONTRACTS["table_constraints"],
            "table_constraints",
            self.model.table_constraints(),
        )

    def table_options(self) -> Any:
        """The selected table-options declaration (§5.6: first applicable)."""
        return self.selector.select(
            TABLE_CONTRACTS["table_options"], "table_options", self.model.table_options()
        )

    def storage_options(self) -> Any:
        """The selected storage-options declaration (§5.6: first applicable)."""
        return self.selector.select(
            TABLE_CONTRACTS["table_storage_options"],
            "table_storage_options",
            self.model.table_storage_options(),
        )

    def partition(self) -> Any:
        """The selected partition declaration (§5.6: first applicable)."""
        return self.selector.select(
            TABLE_CONTRACTS["table_partition"], "table_partition", self.model.table_partition()
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
        constraints = self.column_constraints(field, data_type)
        attributes = self.selected_column_attributes(field)
        constraints = self._apply_identity_nullability(field, constraints, attributes)
        options = self.selector.select(
            COLUMN_CONTRACTS["column_options"], "column_options", self.model.column_options(field)
        )
        column_cls = (
            options.column_definition_class() if options is not None else ColumnDefinition
        )
        name = self.model.column_name(field)
        COLUMN_CONTRACTS["column_name"].validate(name, "column_name")
        column = column_cls(
            self.dialect,
            name,
            data_type,
            constraints=constraints,
            comment=self.selector.select(
                COLUMN_CONTRACTS["column_comment"], "column_comment", self.model.column_comment(field)
            ),
            generated_expression=self.selector.select(
                COLUMN_CONTRACTS["generated_column"],
                "generated_column",
                self.model.generated_column(field),
            ),
            attributes=attributes,
        )
        if options is not None:
            options.apply_to(column)
        return column

    def selected_column_attributes(self, field: str) -> List[Any]:
        """The column's declared attributes, selected by the dialect (§5.3).

        The declared candidates are handed to the dialect's
        ``select_column_attributes`` protocol method, which filters them down
        to the renderable ones (foreign-backend candidates are skipped; an
        owned/generic candidate this dialect cannot render raises).
        """
        attributes = self.model.column_attributes(field)
        if not attributes:
            return []
        return self.dialect.select_column_attributes(attributes)

    def _apply_identity_nullability(
        self,
        field: str,
        constraints: List[ColumnConstraint],
        attributes: List[Any],
    ) -> List[ColumnConstraint]:
        """§5.7: an identity column is forced ``NOT NULL``.

        Explicit ``NOT NULL`` wins (nothing is added); a contradictory
        explicit ``NULL`` is discarded — an identity column is NOT NULL by
        definition, so keeping both would render invalid SQL.
        """
        if not any(getattr(attr, "kind", "") == "identity" for attr in attributes):
            return constraints
        constraints = [
            constraint
            for constraint in constraints
            if constraint.constraint_type != ColumnConstraintType.NULL
        ]
        declared_types = {constraint.constraint_type for constraint in constraints}
        if ColumnConstraintType.NOT_NULL not in declared_types:
            constraints.append(ColumnConstraint(self.dialect, ColumnConstraintType.NOT_NULL))
        return constraints

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
