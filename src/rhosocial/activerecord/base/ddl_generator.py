# src/rhosocial/activerecord/base/ddl_generator.py
"""
Model-level DDL generation (Phase 2 of the "derive DDL from ActiveRecord" plan).

Bridges the gap between an ``ActiveRecord`` model declaration and the
expression-layer ``CreateTableExpression``:

    User.generate_ddl()  →  "CREATE TABLE users (...);"

The generator walks the model's Pydantic ``model_fields`` in declaration order
and, for each field, derives a ``ColumnDefinition``:

1. **Column name** from ``ColumnNameMixin`` (honours ``UseColumn``).
2. **SQL type** from the ``UseSqlType`` annotation if present, otherwise via
   ``dialect.suggest_column_type(python_type)`` (backed by the backend-neutral
   ``DDLTypeSuggestionMixin``).
3. **Constraints** from the ``UseConstraint`` annotation plus the primary key
   (and NOT NULL for required fields when appropriate).

Table-level declarations (``TableOptions``, ``__table_indexes__``,
``__table_constraints__``, composite primary key) are assembled directly.

Backend capability is protocolised: features the target dialect does not
support (e.g. a partial index on a backend without partial-index support)
raise ``UnsupportedFeatureError``; the caller decides how to degrade.
"""

from typing import Any, Dict, List, Optional, Type

from ..backend.dialect.mixins.ddl_type import _NEUTRAL_TYPE_SUGGESTIONS
from ..backend.expression.types import IntegerType
from ..backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
    TableConstraint,
    TableConstraintType,
    TableOptions,
)
from .fields import UseSqlType


def _python_type_of(field: Any) -> Optional[Type]:
    """Return the concrete Python type of a Pydantic field annotation.

    Strips ``Optional[T]`` / ``Union[T, None]`` wrappers so the dialect can map
    the innermost type. Returns ``None`` when no usable type is found.
    """
    annotation = getattr(field, "annotation", None)
    if annotation is None:
        return None
    return _unwrap_annotation(annotation)


def _unwrap_annotation(annotation: Any) -> Optional[Type]:
    """Recursively unwrap ``Optional[T]`` / ``Union`` to a concrete type."""
    import typing

    origin = typing.get_origin(annotation)
    if origin is typing.Union:
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return _unwrap_annotation(args[0])
        return None
    if isinstance(annotation, type):
        return annotation
    return None


def _is_optional_annotation(annotation: Any) -> bool:
    """Return whether an annotation is ``Optional[T]`` (nullable)."""
    import typing

    origin = typing.get_origin(annotation)
    if origin is typing.Union:
        return any(a is type(None) for a in typing.get_args(annotation))
    return False


class ModelSchemaGenerator:
    """Turn an ``ActiveRecord`` model into a ``CreateTableExpression``.

    The generator's job is to *produce the expression instance*, not to emit
    SQL. Callers receive a ``CreateTableExpression`` and may call ``.to_sql()``
    (or otherwise transform / inspect it) as they see fit.

    Callers normally use the ``ActiveRecord.generate_ddl()`` classmethod, which
    is a thin wrapper around :meth:`generate`.
    """

    @classmethod
    def generate(
        cls,
        model_class: type,
        dialect: Any,
        *,
        if_not_exists: bool = False,
        temporary: bool = False,
    ) -> CreateTableExpression:
        """Build a ``CreateTableExpression`` for *model_class* under *dialect*."""
        table_name = getattr(model_class, "__table_name__", None) or model_class.__name__
        columns = cls._build_columns(model_class, dialect)
        indexes = list(getattr(model_class, "__ddl_indexes__", []) or [])
        constraints = list(getattr(model_class, "__ddl_constraints__", []) or [])
        table_options = getattr(model_class, "__ddl_table_options__", None)

        pk = cls._build_primary_key_constraint(model_class)
        if pk is not None:
            constraints = list(constraints) + [pk]

        if table_options is not None and not isinstance(table_options, TableOptions):
            raise TypeError(
                f"__table_options__ must be a TableOptions instance, got "
                f"{type(table_options).__name__}"
            )

        return CreateTableExpression(
            dialect=dialect,
            table=table_name,
            columns=columns,
            indexes=indexes,
            table_constraints=constraints,
            table_options=table_options,
            temporary=temporary,
            if_not_exists=if_not_exists,
        )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    @classmethod
    def _build_columns(cls, model_class: type, dialect: Any) -> List[ColumnDefinition]:
        from pydantic.fields import FieldInfo

        model_fields: Dict[str, FieldInfo] = dict(model_class.model_fields)
        field_sql_types: Dict[str, UseSqlType] = getattr(
            model_class, "__table_field_sql_types__", {}
        )
        field_constraints: Dict[str, List[ColumnConstraint]] = getattr(
            model_class, "__table_field_constraints__", {}
        )

        get_column_name = getattr(model_class, "get_column_name", None)
        pk_columns = set(model_class.primary_key_columns())

        columns: List[ColumnDefinition] = []
        for field_name, field in model_fields.items():
            column_name = (
                get_column_name(field_name) if get_column_name else field_name
            )

            data_type = cls._resolve_data_type(
                field, field_sql_types.get(field_name), dialect
            )

            col_constraints: List[ColumnConstraint] = list(
                field_constraints.get(field_name, [])
            )
            # NOT NULL for required (non-nullable) fields — an ``Optional[T]``
            # field or a field with a default stays nullable.
            if (
                field.is_required()
                and not _is_optional_annotation(getattr(field, "annotation", None))
                and column_name not in pk_columns
            ):
                col_constraints.append(
                    ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL)
                )
            # Single-column PK (not auto-managed via __ddl_constraints__)
            if (
                not model_class.is_composite_pk()
                and column_name in pk_columns
            ):
                col_constraints.append(
                    cls._primary_key_column_constraint(model_class, field_name)
                )

            columns.append(
                ColumnDefinition(
                    name=column_name,
                    data_type=data_type,
                    constraints=col_constraints,
                )
            )

        return columns

    @classmethod
    def _resolve_data_type(
        cls,
        field: Any,
        use_sql_type: Optional[UseSqlType],
        dialect: Any,
    ) -> Any:
        """Resolve a field's SQL ``DataType``, honouring per-dialect overrides."""
        dialect_name = getattr(dialect, "name", None)
        if use_sql_type is not None:
            resolved = use_sql_type.resolve(dialect_name)
            if resolved is not None:
                return resolved
            # Fall through to suggestion if UseSqlType has no applicable type.
        python_type = _python_type_of(field)
        suggest = getattr(dialect, "suggest_column_type", None)
        if suggest is not None and python_type is not None:
            # Read the raw server version without triggering the dialect's
            # "not adapted" exception; None when the dialect is unconnected.
            server_version = getattr(dialect, "_version", None)
            suggested = suggest(python_type, server_version)
            if suggested is not None:
                return suggested
        # Dialect returned None (or has no suggestion support): fall back to
        # the backend-neutral suggestion map instead of silently using INT.
        if python_type is not None and python_type in _NEUTRAL_TYPE_SUGGESTIONS:
            return _NEUTRAL_TYPE_SUGGESTIONS[python_type]
        # Ultimate neutral fallback.
        return IntegerType()

    @staticmethod
    def _primary_key_column_constraint(
        model_class: type, field_name: str
    ) -> ColumnConstraint:
        """Build a PK constraint for a single-column primary key field.

        Auto-increment is applied when the model's PK is auto-generated and
        the backing Python type is integer-like.
        """
        auto = bool(getattr(model_class, "__pk_auto_generated__", False))
        if auto:
            field = model_class.model_fields.get(field_name)
            python_type = _python_type_of(field) if field else None
            if python_type is None or not issubclass(python_type, int):
                auto = False
        return ColumnConstraint(
            constraint_type=ColumnConstraintType.PRIMARY_KEY,
            is_auto_increment=auto,
        )

    # ------------------------------------------------------------------
    # Primary key (composite)
    # ------------------------------------------------------------------
    @staticmethod
    def _build_primary_key_constraint(model_class: type) -> Optional[TableConstraint]:
        """Return a composite-PK ``TableConstraint``, or ``None`` for single-column."""
        if not model_class.is_composite_pk():
            return None
        columns = list(model_class.primary_key_columns())
        return TableConstraint(
            constraint_type=TableConstraintType.PRIMARY_KEY,
            columns=columns,
        )