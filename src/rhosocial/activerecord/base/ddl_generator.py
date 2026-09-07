# src/rhosocial/activerecord/base/ddl_generator.py
"""
Model-level DDL generation (Phase 2 of the "derive DDL from ActiveRecord" plan).

Bridges the gap between an ``ActiveRecord`` model declaration and the
expression-layer DDL statements:

    User.generate_create_table()  →  CreateTableExpression
    User.generate_drop_table()    →  DropTableExpression

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
from ..backend.expression.statements.ddl_spec import (
    DDLSpec, DefaultSpec, GeneratedColumnSpec, JsonColumnSpec, NotNullSpec,
)
from ..backend.expression.types import IntegerType
from ..backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
    DropTableExpression,
    IndexDefinition,
    TableConstraint,
    TableConstraintType,
    TableOptions,
)
from .fields import UseConstraint, UseIndex, UseSqlType


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
    """Recursively unwrap ``Optional[T]`` / ``Union`` to a concrete type.

    ``Enum`` subclasses are normalised to the ``enum.Enum`` base so backend
    ``suggest_column_type`` mappings keyed on ``enum.Enum`` (and the neutral
    map) match real enum types instead of silently degrading to ``INTEGER``.
    """
    import enum
    import typing

    origin = typing.get_origin(annotation)
    if origin is typing.Union:
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return _unwrap_annotation(args[0])
        return None
    if isinstance(annotation, type):
        if issubclass(annotation, enum.Enum):
            return enum.Enum
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
    """Turn an ``ActiveRecord`` model into DDL statement expressions.

    The generator's job is to *produce expression instances*, not to emit
    SQL. Callers receive a ``CreateTableExpression`` (via
    :meth:`generate_create_table`) or a ``DropTableExpression`` (via
    :meth:`generate_drop_table`) and may call ``.to_sql()``
    (or otherwise transform / inspect them) as they see fit.

    Callers normally use the ``ActiveRecord.generate_create_table()`` /
    ``ActiveRecord.generate_drop_table()`` classmethods, which are thin
    wrappers around :meth:`generate_create_table` / :meth:`generate_drop_table`.
    """

    @classmethod
    def generate_create_table(
        cls,
        model_class: type,
        dialect: Any,
        *,
        if_not_exists: bool = False,
        temporary: bool = False,
    ) -> CreateTableExpression:
        """Build a ``CreateTableExpression`` for *model_class* under *dialect*."""
        table_name = getattr(model_class, "__table_name__", None) or model_class.__name__
        constraints_specs = list(getattr(model_class, "__table_constraints__", []) or [])
        indexes_specs = list(getattr(model_class, "__table_indexes__", []) or [])
        # __primary_key__ metadata takes precedence: a PrimaryKeySpec agreeing
        # with it is an explicit no-op; a conflicting one is a declaration
        # error (fail fast rather than silently choosing).
        cls._validate_pk_spec(model_class, constraints_specs)
        # Field-level UseIndex markers join the table-level declarations.
        indexes_specs += cls._collect_field_indexes(model_class)
        # Column-level Specs are consumed while building each column.
        columns = cls._build_columns(model_class, dialect, table_specs=constraints_specs)
        # Record generated columns on the model so INSERT/UPDATE skip them.
        model_class.__table_generated_columns__ = tuple(
            col.name for col in columns if col.generated_expression is not None
        )
        # Spec products are routed by kind, making the two declaration slots
        # interchangeable: index products (IndexDefinition, e.g. from
        # IndexSpec / PartialIndexSpec declared in either slot) always land in
        # ``indexes``; every other product lands in ``table_constraints``.
        index_slot = cls._resolve_spec_list(indexes_specs, dialect)
        constraint_slot = cls._resolve_spec_list(constraints_specs, dialect)
        indexes = (
            [e for e in index_slot if isinstance(e, IndexDefinition)]
            + [e for e in constraint_slot if isinstance(e, IndexDefinition)]
        )
        constraints = (
            [e for e in constraint_slot if not isinstance(e, IndexDefinition)]
            + [e for e in index_slot if not isinstance(e, IndexDefinition)]
        )
        partition = cls._build_partition(model_class, dialect)
        table_options = getattr(model_class, "__table_options__", None)

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
            partition=partition,
            table_options=table_options,
            temporary=temporary,
            if_not_exists=if_not_exists,
        )

    @classmethod
    def _collect_field_indexes(cls, model_class: type) -> List[Any]:
        """Collect single-column indexes declared via field-level
        ``UseIndex`` markers (read from Pydantic's preserved metadata)."""

        collected: List[Any] = []
        get_column_name = getattr(model_class, "get_column_name", None)
        for field_name, field in model_class.model_fields.items():
            column_name = (
                get_column_name(field_name) if get_column_name else field_name
            )
            for marker in field.metadata:
                if isinstance(marker, UseIndex):
                    collected.append(marker.to_index_definition(column_name))
        return collected

    @classmethod
    def _validate_pk_spec(cls, model_class: type, constraints_specs: List[Any]) -> None:
        """Check ``PrimaryKeySpec`` declarations against ``__primary_key__``.

        The model's PK metadata always wins: a ``PrimaryKeySpec`` naming the
        same column(s) is a redundant explicit restatement (allowed); one
        naming different columns conflicts with the metadata and raises.
        """
        from ..backend.expression.statements.ddl_spec import PrimaryKeySpec

        declared = set(model_class.primary_key_columns())
        for entry in constraints_specs:
            if not isinstance(entry, PrimaryKeySpec):
                continue
            spec_cols = set(entry.columns)
            if spec_cols != declared:
                raise ValueError(
                    f"PrimaryKeySpec {sorted(spec_cols)} conflicts with the "
                    f"model's __primary_key__ {sorted(declared)} on "
                    f"'{model_class.__name__}'. __primary_key__ takes "
                    f"precedence; align the Spec or remove it."
                )

    @classmethod
    def _resolve_spec_list(cls, entries: List[Any], dialect: Any) -> List[Any]:
        """Resolve ``DDLSpec`` entries through ``dialect.build_spec``.

        Pre-built expression objects pass through unchanged; Specs the dialect
        does not claim (``build_spec`` returns ``None``) are silently ignored.
        A pre-built ``IndexDefinition`` carrying a lazy ``partial_condition``
        factory is resolved in place.
        """
        resolvers = cls._dialect_resolvers(dialect)
        resolved: List[Any] = []
        for entry in entries:
            if isinstance(entry, DDLSpec):
                built = dialect.build_spec(entry)
                if built is not None:
                    resolved.append(built)
            elif isinstance(entry, IndexDefinition):
                if entry.partial_condition is not None:
                    entry.partial_condition = resolvers["predicate"](
                        entry.partial_condition
                    )
                resolved.append(entry)
            else:
                resolved.append(entry)
        return resolved


    @classmethod
    def _build_partition(cls, model_class: type, dialect: Any) -> Optional[Any]:
        """Resolve ``__table_partition__`` Specs to a single partition clause.

        The first backend-claimed partition Spec wins; unclaimed ones are
        ignored. When nothing is claimed the table is unpartitioned.
        """
        partitions = getattr(model_class, "__table_partition__", []) or []
        for entry in partitions:
            if not isinstance(entry, DDLSpec):
                raise TypeError(
                    f"__table_partition__ entries must be DDLSpec instances, "
                    f"got {type(entry).__name__}"
                )
            built = dialect.build_spec(entry)
            if built is not None:
                return built
        return None

    @classmethod
    def generate_drop_table(
        cls,
        model_class: type,
        dialect: Any,
        *,
        if_exists: bool = False,
        cascade: Optional[bool] = None,
    ) -> DropTableExpression:
        """Build a ``DropTableExpression`` for *model_class* under *dialect*.

        Only the model's table name is derived here — dependent-object behavior
        (``cascade``) is optional and subject to dialect capability gating at
        render time (``UnsupportedFeatureError`` when the dialect does not
        support the requested form).
        """
        table_name = getattr(model_class, "__table_name__", None) or model_class.__name__
        return DropTableExpression(
            dialect=dialect,
            table=table_name,
            if_exists=if_exists,
            cascade=cascade,
        )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    @classmethod
    def _build_columns(
        cls,
        model_class: type,
        dialect: Any,
        table_specs: Optional[List[Any]] = None,
    ) -> List[ColumnDefinition]:
        from pydantic.fields import FieldInfo

        model_fields: Dict[str, FieldInfo] = dict(model_class.model_fields)
        column_specs = cls._collect_column_specs(model_class, table_specs or [])

        get_column_name = getattr(model_class, "get_column_name", None)
        pk_columns = set(model_class.primary_key_columns())

        columns: List[ColumnDefinition] = []
        for field_name, field in model_fields.items():
            column_name = (
                get_column_name(field_name) if get_column_name else field_name
            )

            # Field-level Annotated markers are read straight from Pydantic's
            # preserved metadata — no intermediate collection pass. Multiple
            # UseSqlType markers are rejected (combine types into one marker).
            sql_type_markers = [
                m for m in field.metadata if isinstance(m, UseSqlType)
            ]
            if len(sql_type_markers) > 1:
                raise TypeError(
                    f"Field {field_name!r} declares multiple UseSqlType "
                    f"markers. Combine the types into a single "
                    f"UseSqlType(type_a, type_b, ...) instead."
                )
            sql_type = sql_type_markers[0] if sql_type_markers else None
            data_type = cls._resolve_data_type(field, sql_type, dialect)

            col_constraints: List[ColumnConstraint] = [
                m.constraint
                for m in field.metadata
                if isinstance(m, UseConstraint)
            ]
            col_constraints = [
                cls._resolve_field_constraint(c, dialect) for c in col_constraints
            ]
            gen_type = None
            gen_expression = None
            # Column-level Specs for this column (NotNull/Default/Json/Generated)
            for spec in column_specs.get(column_name, []):
                if isinstance(spec, NotNullSpec):
                    col_constraints.append(
                        ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL)
                    )
                elif isinstance(spec, DefaultSpec):
                    from ..backend.expression.core import Literal

                    col_constraints.append(
                        ColumnConstraint(
                            constraint_type=ColumnConstraintType.DEFAULT,
                            default_value=Literal(
                                dialect, cls._resolve_spec_value(dialect, spec.value)
                            ),
                        )
                    )
                elif isinstance(spec, JsonColumnSpec):
                    from ..backend.expression.types import JsonType

                    data_type = JsonType(dialect)
                elif isinstance(spec, GeneratedColumnSpec):
                    if cls._supports(dialect, "supports_generated_columns"):
                        from ..backend.expression.statements import GeneratedColumnType

                        gen_expression = cls._resolve_spec_value(dialect, spec.expression)
                        gen_type = (
                            GeneratedColumnType.STORED if spec.stored
                            else GeneratedColumnType.VIRTUAL
                        )
            # NOT NULL for required (non-nullable) fields — an ``Optional[T]``
            # field or a field with a default stays nullable. Skip when the
            # field already declares NOT NULL via UseConstraint/NotNullSpec
            # (avoids rendering a duplicated "NOT NULL NOT NULL").
            if (
                field.is_required()
                and not _is_optional_annotation(getattr(field, "annotation", None))
                and column_name not in pk_columns
                and not any(
                    c.constraint_type == ColumnConstraintType.NOT_NULL
                    for c in col_constraints
                )
            ):
                col_constraints.append(
                    ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL)
                )
            # Single-column PK (not auto-managed via __table_constraints__)
            if (
                not model_class.is_composite_pk()
                and column_name in pk_columns
            ):
                col_constraints.append(
                    cls._primary_key_column_constraint(model_class, field_name)
                )

            # Apply capability patches (JSON type / generated column) if any.
            col_def_kwargs: Dict[str, Any] = {
                "name": column_name,
                "data_type": data_type,
                "constraints": col_constraints,
            }
            if gen_type is not None:
                col_def_kwargs["generated_expression"] = gen_expression
                col_def_kwargs["generated_type"] = gen_type

            columns.append(ColumnDefinition(**col_def_kwargs))

        return columns

    @staticmethod
    def _supports(dialect: Any, capability: str) -> bool:
        """Check a ``supports_*()`` capability, tolerating unadapted dialects
        (assume available: DDL generation produces expressions; the render
        step and the real database validate actual availability)."""
        method = getattr(dialect, capability, None)
        if method is None:
            return False
        try:
            return bool(method())
        except Exception:
            return True

    @classmethod
    def _collect_column_specs(cls, model_class: type, table_specs: List[Any]) -> Dict[str, List[Any]]:
        """Collect column-level Specs by column name.

        Sources: ``NotNullSpec`` / ``DefaultSpec`` / ``JsonColumnSpec`` /
        ``GeneratedColumnSpec`` declared in ``__table_constraints__``.
        """
        collected: Dict[str, List[Any]] = {}
        column_level = (
            NotNullSpec, DefaultSpec, JsonColumnSpec, GeneratedColumnSpec,
        )
        for entry in table_specs:
            if not isinstance(entry, column_level):
                continue
            column = entry.column
            collected.setdefault(column, []).append(entry)
        return collected

    @classmethod
    def _resolve_spec_value(cls, dialect: Any, value: Any) -> Any:
        """Evaluate a lazy ``(dialect) -> Any`` value factory, or pass through."""
        if callable(value) and not hasattr(value, "to_sql"):
            return value(dialect)
        return value

    @classmethod
    def _resolve_field_constraint(cls, constraint: ColumnConstraint, dialect: Any) -> ColumnConstraint:
        """Resolve a lazy ``(dialect) -> SQLPredicate`` in a field constraint's
        ``check_condition`` (and ``default_value``) at generation time.

        Field-level annotations are declared without a dialect; the predicate
        factory is evaluated here, where the dialect is known.
        """
        resolvers = cls._dialect_resolvers(dialect)
        constraint.check_condition = resolvers["predicate"](constraint.check_condition)
        if constraint.default_value is not None and callable(constraint.default_value) \
                and not hasattr(constraint.default_value, "to_sql"):
            constraint.default_value = resolvers["value"](constraint.default_value)
        return constraint

    @classmethod
    def _dialect_resolvers(cls, dialect: Any) -> Dict[str, Any]:
        """Return the dialect's predicate / value factory resolvers when present,
        else pass-through identity functions."""
        return {
            "predicate": getattr(dialect, "_resolve_predicate", lambda x: x),
            "value": getattr(dialect, "_resolve_value", lambda x: x),
        }

    @classmethod
    def _resolve_data_type(
        cls,
        field: Any,
        use_sql_type: Optional[UseSqlType],
        dialect: Any,
    ) -> Any:
        """Resolve a field's SQL ``DataType``.

        When a ``UseSqlType`` declaration is present, the first declared type
        the current dialect can render is selected (declaration order = backend
        priority). If none matches, the dialect's own type suggestion for the
        field's Python type is consulted; if that also yields nothing, an error
        is raised (the user explicitly declared types, so we do not silently
        substitute a neutral fallback).

        Without a declaration, the dialect's suggestion is used, then the
        backend-neutral map, then ``IntegerType`` as a last resort.
        """
        if use_sql_type is not None:
            selected = cls._select_supported_type(use_sql_type.data_types, dialect)
            if selected is not None:
                return selected
            python_type = _python_type_of(field)
            suggest = getattr(dialect, "suggest_column_type", None)
            if suggest is not None and python_type is not None:
                server_version = getattr(dialect, "_version", None)
                suggested = suggest(python_type, server_version)
                if suggested is not None:
                    return suggested
            dialect_name = getattr(dialect, "name", type(dialect).__name__)
            declared = ", ".join(
                f"{type(t).__module__}.{type(t).__qualname__}"
                for t in use_sql_type.data_types
            )
            raise TypeError(
                f"{dialect_name}: none of the declared UseSqlType types is "
                f"renderable here ({declared}) and there is no suggested type "
                f"for {python_type or 'unknown'}. Declare a type this backend "
                f"supports or remove the declaration to use the backend default."
            )
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
    def _select_supported_type(data_types: tuple, dialect: Any) -> Optional[Any]:
        """Return the first declared type the dialect can render, else None."""
        supports = getattr(dialect, "supports_data_type", None)
        if supports is None:
            return None
        for dt in data_types:
            if supports(dt):
                return dt
        return None

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