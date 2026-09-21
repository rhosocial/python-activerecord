# src/rhosocial/activerecord/base/ddl/mixin.py
"""Model-facing DDL interfaces and entry points.

Every declaration interface is an overridable classmethod: the default is
inferred by the framework, and an application may override it to take over. All
interfaces return expressions (or lists of expressions) that are **directly
usable as DDL construction parameters** (§5.5); the dialect is injected by the
deriver at build time, so whether a declaration carries one is irrelevant.

Declaration surfaces (§5.4/§5.8): **single-field** semantics are declared on
field annotations (``UseColumn`` / ``UseSqlType`` / ``UseConstraint`` /
``UseColumnAttributes`` / ``UseIndex``) and read through the
``column_*(field)`` primitives; **cross-field / table-level** semantics are
declared on class constants (``__table_indexes__`` / ``__table_constraints__``)
or classmethods and read through the ``table_*()`` interfaces. The
``columns_*(fields=None)`` batch interfaces walk the primitives.
"""

from __future__ import annotations

import warnings
from typing import Any, ClassVar, Dict, List, Optional, Type

from .annotations import DDLAnnotationHandler, DDLFieldMetadata
from .deriver import TableDDLDeriver
from .plans import DDLPlan
from ..fields import UseIndex
from ...backend.expression.statements.ddl_index import CreateIndexExpression, DropIndexExpression
from ...backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    CreateTableExpression,
    DropTableExpression,
    IndexDefinition,
    TableConstraint,
    TableConstraintType,
)


class DDLMixin:
    """Overridable DDL declaration interfaces with framework-inferred defaults."""

    _feature_handlers = [DDLAnnotationHandler]

    __table_ddl_fields__: ClassVar[Dict[str, DDLFieldMetadata]] = {}

    # ----- table-level interfaces -----

    @classmethod
    def table_options(cls) -> Any:
        """Table options declaration (``CreateTableOptions`` or a subclass)."""
        return None

    @classmethod
    def table_storage_options(cls) -> Any:
        """Storage-options declaration (``StorageOptionsExpression``)."""
        return None

    @classmethod
    def table_partition(cls) -> Any:
        """Partition declaration (``PartitionClause`` or backend subclass(es))."""
        return None

    @classmethod
    def table_indexes(cls) -> List[IndexDefinition]:
        """Table-level (composite) index declarations (§5.4).

        Defaults to the ``__table_indexes__`` constant — a list of dialect-free
        ``IndexDefinition`` objects. Field-level (single-column) indexes are
        declared through ``UseIndex`` and collected separately (see
        :meth:`column_indexes`); the deriver merges both sources and dedups
        them by name.
        """
        return list(getattr(cls, "__table_indexes__", ()) or [])

    @classmethod
    def table_constraints(cls) -> List[TableConstraint]:
        """Table-level (composite) constraint declarations (§5.4).

        Defaults to the ``__table_constraints__`` constant — a list of
        dialect-free ``TableConstraint`` objects (composite UNIQUE / CHECK /
        FOREIGN KEY) — plus the composite primary key, which is derived from
        the ``__primary_key__`` constant (§5.2) and rendered as a table-level
        ``PRIMARY KEY`` constraint.
        """
        declarations = list(getattr(cls, "__table_constraints__", ()) or [])
        if cls.is_composite_pk():
            declarations.append(
                TableConstraint(
                    None,
                    TableConstraintType.PRIMARY_KEY,
                    columns=list(cls.primary_key_columns()),
                )
            )
        return declarations

    @classmethod
    def index_definition(cls, marker: UseIndex, column_name: str) -> IndexDefinition:
        """Build a dialect-free ``IndexDefinition`` from a field's ``UseIndex``."""
        return IndexDefinition(
            None,
            name=marker.name,
            columns=[column_name],
            unique=marker.unique,
            type=marker.type,
            partial_condition=marker.partial_condition,
            include_columns=marker.include_columns,
        )

    # ----- statement-family candidate overrides (§5.12) -----

    @classmethod
    def create_table_statement_classes(cls) -> Optional[List[Type[CreateTableExpression]]]:
        """Optional candidate ``CREATE TABLE`` statement classes (§5.12).

        ``None`` (default) lets the deriver compose the candidates from the
        dialect protocol's preferred class plus the generic form. A model may
        override with its own list (generic + backend-specific combination,
        order = priority — the most fitting candidate wins through Gate 1
        ownership + Gate 2 renderability; all inapplicable raises).
        """
        return None

    @classmethod
    def drop_table_statement_classes(cls) -> Optional[List[Type[DropTableExpression]]]:
        """Optional candidate ``DROP TABLE`` statement classes (§5.12)."""
        return None

    @classmethod
    def create_index_statement_classes(cls) -> Optional[List[Type[CreateIndexExpression]]]:
        """Optional candidate ``CREATE INDEX`` statement classes (§5.12)."""
        return None

    @classmethod
    def drop_index_statement_classes(cls) -> Optional[List[Type[DropIndexExpression]]]:
        """Optional candidate ``DROP INDEX`` statement classes (§5.12)."""
        return None

    # ----- column-level primitives (column_*(field)) -----

    @classmethod
    def column_name(cls, field: str) -> str:
        """Physical column name for a field (default: ``UseColumn`` mapping)."""
        return cls.get_column_name(field)

    @classmethod
    def column_type(cls, field: str) -> Any:
        """Declared column type candidates; ``None`` uses the canonical mapping.

        Returns the raw declaration (a ``UseSqlType`` marker, a ``DataType``,
        or a list of them) — dialect-free candidates the deriver resolves per
        dialect through the type resolver.
        """
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        return metadata.use_sql_type if metadata is not None else None

    @classmethod
    def column_constraints(cls, field: str) -> List[ColumnConstraint]:
        """Column constraints for a field (nullability per §5.7).

        Defaults to the field's ``UseConstraint`` declarations plus the
        framework-inferred nullability:

        - explicit ``NOT NULL`` / ``NULL`` wins over any inference;
        - primary-key members are **forced** ``NOT NULL`` (an explicit
          ``NULL`` on a PK column is discarded — a PRIMARY KEY column is NOT
          NULL by definition);
        - ``Optional[T]`` adds **no** clause (nullable);
        - required ``T`` adds ``NOT NULL``.

        The primary key itself has a single source (``__primary_key__``, §5.2):
        a single-column PK lands the ``PRIMARY KEY`` constraint on the column,
        a composite PK becomes a table-level constraint (§5.4).
        """
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        if metadata is None:
            return []
        constraints = [marker.constraint for marker in metadata.constraints]
        declared_types = {constraint.constraint_type for constraint in constraints}
        explicit_not_null = ColumnConstraintType.NOT_NULL in declared_types
        explicit_nullable = ColumnConstraintType.NULL in declared_types
        pk_member = cls.column_name(field) in cls.primary_key_columns()
        if pk_member and not cls.is_composite_pk():
            # §5.2: a single-column PK lands the PRIMARY KEY constraint on
            # the column; a composite PK becomes a table-level constraint.
            constraints.append(ColumnConstraint(None, ColumnConstraintType.PRIMARY_KEY))
        if pk_member:
            # §5.7: PK members are forced NOT NULL; a contradictory explicit
            # NULL is discarded (a PRIMARY KEY column is NOT NULL by
            # definition, so keeping both would render invalid SQL).
            if explicit_nullable:
                constraints = [
                    constraint
                    for constraint in constraints
                    if constraint.constraint_type != ColumnConstraintType.NULL
                ]
            if not explicit_not_null:
                constraints.append(ColumnConstraint(None, ColumnConstraintType.NOT_NULL))
        elif not explicit_not_null and not explicit_nullable and not metadata.is_optional:
            constraints.append(ColumnConstraint(None, ColumnConstraintType.NOT_NULL))
        return constraints

    @classmethod
    def column_attributes(cls, field: str) -> List[Any]:
        """Column attributes for a field (``ColumnAttribute`` subclasses).

        Defaults to the field's ``UseColumnAttributes`` declarations —
        dialect-free candidates (identity, collation, character set, …) the
        deriver hands to the dialect, which selects the renderable ones (§5.3).
        """
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        if metadata is None:
            return []
        return [
            attribute
            for marker in metadata.column_attributes
            for attribute in marker.attributes
        ]

    @classmethod
    def column_indexes(cls, field: str) -> List[IndexDefinition]:
        """Field-level (single-column) index declarations for a field (§5.4).

        Defaults to the field's ``UseIndex`` markers, built into dialect-free
        ``IndexDefinition`` objects. Composite indexes are declared through
        ``__table_indexes__`` (§5.8); the deriver merges both sources.
        """
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        if metadata is None:
            return []
        return [cls.index_definition(marker, cls.column_name(field)) for marker in metadata.indexes]

    @classmethod
    def column_comment(cls, field: str) -> Optional[str]:
        """Column comment; default none."""
        return None

    @classmethod
    def generated_column(cls, field: str) -> Any:
        """Generated-column declaration (``GeneratedColumnExpression``)."""
        return None

    @classmethod
    def column_options(cls, field: str) -> Any:
        """Backend-specific column options (``ColumnOptions``), or a list of
        candidates — the first applicable one wins (order = priority, §5.6)."""
        return None

    # ----- batch access (columns_*(fields=None) -> Dict) -----

    @classmethod
    def _batch_fields(cls, fields: Optional[List[str]]) -> List[str]:
        """The fields a batch interface visits (all model fields by default)."""
        if fields is None:
            return list(cls.model_fields)
        return list(fields)

    @classmethod
    def columns_name(cls, fields: Optional[List[str]] = None) -> Dict[str, str]:
        """Batch access: field → :meth:`column_name`."""
        return {field: cls.column_name(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_type(cls, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Batch access: field → :meth:`column_type`."""
        return {field: cls.column_type(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_constraints(cls, fields: Optional[List[str]] = None) -> Dict[str, List[ColumnConstraint]]:
        """Batch access: field → :meth:`column_constraints`."""
        return {field: cls.column_constraints(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_attributes(cls, fields: Optional[List[str]] = None) -> Dict[str, List[Any]]:
        """Batch access: field → :meth:`column_attributes`."""
        return {field: cls.column_attributes(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_indexes(cls, fields: Optional[List[str]] = None) -> Dict[str, List[IndexDefinition]]:
        """Batch access: field → :meth:`column_indexes`."""
        return {field: cls.column_indexes(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_comment(cls, fields: Optional[List[str]] = None) -> Dict[str, Optional[str]]:
        """Batch access: field → :meth:`column_comment`."""
        return {field: cls.column_comment(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_generated(cls, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Batch access: field → :meth:`generated_column`."""
        return {field: cls.generated_column(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_options(cls, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Batch access: field → :meth:`column_options`."""
        return {field: cls.column_options(field) for field in cls._batch_fields(fields)}

    # ----- entry points -----

    @classmethod
    def _deriver(cls) -> TableDDLDeriver:
        """Build a deriver bound to this model's backend dialect (internal).

        The deriver is an implementation detail: the model-facing surface is
        the declaration interfaces plus the plan/statement entry points below.
        """
        return TableDDLDeriver(cls, cls.backend().dialect)

    @classmethod
    def create_table(
        cls,
        *,
        if_not_exists: bool = False,
        temporary: bool = False,
        inline_indexes: Optional[bool] = None,
    ) -> CreateTableExpression:
        """Return the ``CREATE TABLE`` expression derived from this model.

        Args:
            if_not_exists: Add IF NOT EXISTS clause.
            temporary: Build a TEMPORARY table.
            inline_indexes: Advanced override — whether to carry inline index
                definitions. ``None`` (default) auto-routes by the backend
                dialect's ``supports_inline_index()`` capability; ``True``
                forces inline indexes (rendering raises
                UnsupportedFeatureError on dialects without inline-index
                support); ``False`` forces standalone CREATE INDEX statements
                even on inline-capable dialects.
        """
        return cls._deriver().create_table(
            if_not_exists=if_not_exists, temporary=temporary,
            inline_indexes=inline_indexes,
        )

    @classmethod
    def create_indexes(cls) -> List[CreateIndexExpression]:
        """Return standalone ``CREATE INDEX`` expressions for this model.

        Empty on inline-capable dialects (indexes ride inside CREATE TABLE),
        so ``create_table()`` + ``create_indexes()`` never create an index
        twice.
        """
        return cls._deriver().create_indexes()

    @classmethod
    def drop_indexes(cls, *, if_exists: bool = False) -> List[DropIndexExpression]:
        """Return ``DROP INDEX`` expressions for every declared index.

        Args:
            if_exists: Add IF EXISTS clause.
        """
        return cls._deriver().drop_indexes(if_exists=if_exists)

    @classmethod
    def creation_plan(cls) -> DDLPlan:
        """Return the full creation plan (§5.4/B1): a typed :class:`DDLPlan`
        holding ``CREATE TABLE`` plus any standalone ``CREATE INDEX``
        statements this dialect requires."""
        return DDLPlan([cls.create_table(), *cls.create_indexes()])

    @classmethod
    def teardown_plan(cls) -> DDLPlan:
        """Return the full teardown plan (§5.4/B1): a typed :class:`DDLPlan`
        holding standalone ``DROP INDEX IF EXISTS`` statements followed by
        ``DROP TABLE`` (indexes first, table last)."""
        return DDLPlan([*cls.drop_indexes(if_exists=True), cls.drop_table()])

    @classmethod
    def create_schema(cls) -> List[Any]:
        """Deprecated alias of :meth:`creation_plan` (returns the statement
        list); renamed because it is not a ``CREATE SCHEMA`` statement."""
        warnings.warn(
            "create_schema() is deprecated; use creation_plan() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return list(cls.creation_plan())

    @classmethod
    def drop_schema(cls) -> List[Any]:
        """Deprecated alias of :meth:`teardown_plan` (returns the statement
        list); renamed because it is not a ``DROP SCHEMA`` statement."""
        warnings.warn(
            "drop_schema() is deprecated; use teardown_plan() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return list(cls.teardown_plan())

    @classmethod
    def drop_table(
        cls,
        *,
        if_exists: bool = False,
        cascade: Optional[bool] = None,
    ) -> DropTableExpression:
        """Return the ``DROP TABLE`` expression for this model."""
        return cls._deriver().drop_table(if_exists=if_exists, cascade=cascade)

    @classmethod
    def create_table_spec(cls, **kwargs: Any) -> Dict[str, Any]:
        """Serialize this model's ``CREATE TABLE`` expression to a spec dict."""
        from ...backend.expression.serialization import ExpressionSerializer

        return ExpressionSerializer().serialize(cls.create_table(**kwargs))

    @classmethod
    def create_table_from_spec(cls, spec: Dict[str, Any]) -> CreateTableExpression:
        """Rebuild a ``CREATE TABLE`` expression from a frozen spec dict."""
        from ...backend.expression.serialization import ExpressionSerializer

        expression = ExpressionSerializer().deserialize(spec, cls.backend().dialect)
        if not isinstance(expression, CreateTableExpression):
            raise TypeError(
                f"Spec resolves to {type(expression).__name__}, not CreateTableExpression."
            )
        return expression
