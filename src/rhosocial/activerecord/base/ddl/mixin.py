# src/rhosocial/activerecord/base/ddl/mixin.py
"""Model-facing DDL interfaces and entry points.

Every declaration interface is an overridable classmethod: the default is
inferred by the framework, and an application may override it to take over. All
interfaces return expressions (or lists of expressions); the dialect is injected
by the deriver at build time, so whether a declaration carries one is irrelevant.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from .annotations import DDLAnnotationHandler, DDLFieldMetadata
from .deriver import TableDDLDeriver
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
        """Composite indexes; defaults to field-level ``UseIndex`` markers."""
        declarations = list(getattr(cls, "__table_indexes__", ()) or [])
        metadata = getattr(cls, "__table_ddl_fields__", {}) or {}
        for field in cls.model_fields:
            field_metadata = metadata.get(field)
            if field_metadata is None:
                continue
            for marker in field_metadata.indexes:
                declarations.append(cls.index_definition(marker, cls.column_name(field)))
        return declarations

    @classmethod
    def table_constraints(cls) -> List[TableConstraint]:
        """Table-level constraints; defaults to the composite primary key."""
        if cls.is_composite_pk():
            return [
                TableConstraint(
                    None,
                    TableConstraintType.PRIMARY_KEY,
                    columns=list(cls.primary_key_columns()),
                )
            ]
        return []

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

    # ----- column-level interfaces (unified column_*(field)) -----

    @classmethod
    def column_name(cls, field: str) -> str:
        """Physical column name for a field (default: ``UseColumn`` mapping)."""
        return cls.get_column_name(field)

    @classmethod
    def column_type(cls, field: str) -> Any:
        """Declared column type candidates; ``None`` uses the canonical mapping."""
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        return metadata.use_sql_type if metadata is not None else None

    @classmethod
    def column_constraints(cls, field: str) -> List[ColumnConstraint]:
        """Column constraints; defaults to ``UseConstraint`` + nullability + PK."""
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        if metadata is None:
            return []
        constraints = [marker.constraint for marker in metadata.constraints]
        declared_types = {constraint.constraint_type for constraint in constraints}
        if not cls.is_composite_pk() and cls.column_name(field) in cls.primary_key_columns():
            if ColumnConstraintType.PRIMARY_KEY not in declared_types:
                constraints.append(ColumnConstraint(None, ColumnConstraintType.PRIMARY_KEY))
        if (
            ColumnConstraintType.NOT_NULL not in declared_types
            and ColumnConstraintType.NULL not in declared_types
            and metadata.is_optional
        ):
            constraints.append(ColumnConstraint(None, ColumnConstraintType.NULL))
        return constraints

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
        """Backend-specific column options (``ColumnOptions``)."""
        return None

    # ----- entry points -----

    @classmethod
    def ddl_deriver(cls) -> TableDDLDeriver:
        """Build a deriver bound to this model's backend dialect."""
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
            inline_indexes: Whether to carry inline index definitions.
                ``None`` (default) follows the backend dialect's
                ``supports_inline_index()`` capability; ``True`` forces inline
                indexes (rendering raises UnsupportedFeatureError on dialects
                without inline-index support); ``False`` forces standalone
                CREATE INDEX statements even on inline-capable dialects.
        """
        return cls.ddl_deriver().create_table(
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
        return cls.ddl_deriver().create_indexes()

    @classmethod
    def drop_indexes(cls) -> List[DropIndexExpression]:
        """Return ``DROP INDEX`` expressions for every declared index."""
        return cls.ddl_deriver().drop_indexes()

    @classmethod
    def create_schema(cls) -> List[Any]:
        """Return the full creation plan: CREATE TABLE plus any standalone
        CREATE INDEX statements this dialect requires."""
        return cls.ddl_deriver().create_schema()

    @classmethod
    def drop_schema(cls) -> List[Any]:
        """Return the full teardown plan: standalone DROP INDEX statements
        followed by DROP TABLE (indexes first, table last)."""
        return cls.ddl_deriver().drop_schema()

    @classmethod
    def drop_table(
        cls,
        *,
        if_exists: bool = False,
        cascade: Optional[bool] = None,
    ) -> DropTableExpression:
        """Return the ``DROP TABLE`` expression for this model."""
        return cls.ddl_deriver().drop_table(if_exists=if_exists, cascade=cascade)

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
