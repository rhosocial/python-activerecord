# src/rhosocial/activerecord/backend/dialect/mixins/ddl_spec.py
"""DDL feature-spec claiming and building (``DDLSpecBuildingMixin``).

Hosted on the dialect because *what a Spec means on this backend* is backend
policy: each backend decides which Specs it accepts and how it translates
them into expression-layer objects. The generic implementation provides a
reasonable, strict default for the core generic Specs (``CheckSpec`` /
``UniqueSpec`` / ``NotNullSpec`` / ``PrimaryKeySpec`` / ``DefaultSpec`` /
``ForeignKeySpec`` / ``IndexSpec``); backends override individual
translations or reject a Spec entirely (return ``None``) when they do not
support it.

Contract:

- ``build_spec(spec)`` returns an expression-layer object
  (``ColumnConstraint`` / ``TableConstraint`` / ``IndexDefinition`` / ...)
  when the dialect accepts the Spec, or ``None`` when it does not. Returning
  ``None`` means the Spec is silently ignored; a backend that considers
  ignoring unsafe may raise inside ``build_spec`` instead.
- ``_resolve_predicate`` / ``_resolve_value`` evaluate lazy
  ``(dialect) -> ...`` factories so declarations stay dialect-free.
"""

from typing import Any, Optional

from ...expression.statements.ddl_spec import (
    CheckSpec,
    ColumnPatchSpec,
    ColumnTypeSpec,
    DDLSpec,
    DefaultSpec,
    ForeignKeySpec,
    GeneratedColumnSpec,
    IndexSpec,
    JsonColumnSpec,
    NotNullSpec,
    PrimaryKeySpec,
    UniqueSpec,
)
from ...expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    ForeignKeyConstraint,
    IndexDefinition,
    TableConstraint,
    TableConstraintType,
)


class DDLSpecBuildingMixin:
    """Turn declarative DDL feature Specs into expression-layer objects.

    Composed into ``SQLDialectBase`` (and thus every backend dialect).
    Backends override :meth:`build_spec` (or individual ``_build_*``
    helpers) to add backend-specific Specs or adjust generic translations.
    """

    def build_spec(self, spec: "DDLSpec") -> Optional[Any]:
        """Accept *spec* and return a built expression object, else ``None``.

        The default implementation handles the core generic Specs and rejects
        everything else (including ``PartitionSpec`` and all backend-defined
        Specs). Backends override to claim more.
        """
        if isinstance(spec, CheckSpec):
            return self._build_check_spec(spec)
        if isinstance(spec, UniqueSpec):
            return self._build_unique_spec(spec)
        if isinstance(spec, NotNullSpec):
            return self._build_not_null_spec(spec)
        if isinstance(spec, PrimaryKeySpec):
            return self._build_primary_key_spec(spec)
        if isinstance(spec, DefaultSpec):
            return self._build_default_spec(spec)
        if isinstance(spec, ForeignKeySpec):
            return self._build_foreign_key_spec(spec)
        if isinstance(spec, IndexSpec):
            return self._build_index_spec(spec)
        if isinstance(spec, GeneratedColumnSpec):
            return self._build_generated_column_spec(spec)
        if isinstance(spec, JsonColumnSpec):
            return self._build_json_column_spec(spec)
        if isinstance(spec, ColumnTypeSpec):
            return self._build_column_type_spec(spec)
        return None

    # ------------------------------------------------------------------
    # Lazy factory resolution
    # ------------------------------------------------------------------
    def _resolve_predicate(self, spec_or_condition: Any) -> Optional[Any]:
        """Evaluate a lazy ``(dialect) -> SQLPredicate`` factory, or pass a
        ready predicate / expression through unchanged."""
        if callable(spec_or_condition) and not hasattr(spec_or_condition, "to_sql"):
            return spec_or_condition(self)
        return spec_or_condition

    def _resolve_value(self, spec_value: Any) -> Any:
        """Evaluate a lazy ``(dialect) -> Any`` value factory, or pass a plain
        value / expression through unchanged."""
        if callable(spec_value) and not hasattr(spec_value, "to_sql"):
            return spec_value(self)
        return spec_value

    # ------------------------------------------------------------------
    # Generic Spec translations
    # ------------------------------------------------------------------
    def _build_check_spec(self, spec: "CheckSpec") -> Optional[Any]:
        """Translate a ``CheckSpec`` to a table-level CHECK constraint.

        The generic form is table-level (``TableConstraint(CHECK)``), which
        is portable; a single-column backend may choose a column-level form
        by overriding.
        """
        condition = self._resolve_predicate(spec.condition)
        if condition is None:
            return None
        return TableConstraint(
            constraint_type=TableConstraintType.CHECK,
            name=spec.name,
            check_condition=condition,
        )

    def _build_unique_spec(self, spec: "UniqueSpec") -> Optional[Any]:
        """Translate a ``UniqueSpec`` to a table-level UNIQUE constraint."""
        return TableConstraint(
            constraint_type=TableConstraintType.UNIQUE,
            name=spec.name,
            columns=list(spec.columns),
        )

    def _build_not_null_spec(self, spec: "NotNullSpec") -> Optional[Any]:
        """Translate a ``NotNullSpec`` to a column-level NOT NULL constraint."""
        return ColumnConstraint(
            constraint_type=ColumnConstraintType.NOT_NULL,
            name=spec.name,
        )

    def _build_primary_key_spec(self, spec: "PrimaryKeySpec") -> Optional[Any]:
        """Translate a ``PrimaryKeySpec``.

        A single column becomes a column-level PK; multiple columns become a
        table-level composite PK constraint.
        """
        if len(spec.columns) == 1:
            return ColumnConstraint(
                constraint_type=ColumnConstraintType.PRIMARY_KEY,
                name=spec.name,
            )
        return TableConstraint(
            constraint_type=TableConstraintType.PRIMARY_KEY,
            name=spec.name,
            columns=list(spec.columns),
        )

    def _build_default_spec(self, spec: "DefaultSpec") -> Optional[Any]:
        """Translate a ``DefaultSpec`` to a column-level DEFAULT constraint.

        Plain values are wrapped in a ``Literal`` (parameterized). Expression
        defaults (e.g. ``nextval``) are backend-specific and belong in backend
        Spec classes — the generic layer never embeds raw SQL.
        """
        from ...expression.core import Literal

        default_value = Literal(self, self._resolve_value(spec.value))
        return ColumnConstraint(
            constraint_type=ColumnConstraintType.DEFAULT,
            name=spec.name,
            default_value=default_value,
        )

    def _build_foreign_key_spec(self, spec: "ForeignKeySpec") -> Optional[Any]:
        """Translate a ``ForeignKeySpec`` to a ``ForeignKeyConstraint``."""
        from ...expression.statements import ReferentialAction

        def _action(value: Optional[str]):
            if value is None:
                return ReferentialAction.NO_ACTION
            try:
                return ReferentialAction(value.upper())
            except ValueError:
                raise ValueError(
                    f"Invalid referential action {value!r}; expected one of "
                    f"{[a.value for a in ReferentialAction]}"
                ) from None

        return ForeignKeyConstraint(
            name=spec.name,
            columns=list(spec.local_columns),
            foreign_key_table=spec.ref_table,
            foreign_key_columns=(
                list(spec.ref_columns) if spec.ref_columns is not None else None
            ),
            on_delete=_action(spec.on_delete),
            on_update=_action(spec.on_update),
        )

    def _build_index_spec(self, spec: "IndexSpec") -> Optional[Any]:
        """Translate an ``IndexSpec`` to an ``IndexDefinition``.

        A partial index is only emitted when the dialect supports partial
        indexes; otherwise ``None`` is returned (silently ignored).
        """
        if spec.partial_condition is not None:
            supports = getattr(self, "supports_partial_index", None)
            if supports is not None:
                try:
                    supported = bool(supports())
                except Exception:
                    # Version-dependent capability on an unadapted dialect:
                    # optimistic — DDL generation only produces the expression;
                    # the render step / real database validates availability.
                    supported = True
                if not supported:
                    return None
        condition = self._resolve_predicate(spec.partial_condition)
        return IndexDefinition(
            name=spec.name,
            columns=list(spec.columns),
            unique=spec.unique,
            type=spec.type,
            partial_condition=condition,
            include_columns=spec.include_columns,
            dialect_options=spec.dialect_options,
        )

    # ------------------------------------------------------------------
    # Capability Spec translations
    # ------------------------------------------------------------------
    def _supports_capability(self, capability: str) -> bool:
        """Check a ``supports_*()`` capability, tolerating unadapted dialects."""
        method = getattr(self, capability, None)
        if method is None:
            return False
        try:
            return bool(method())
        except Exception:
            # Optimistic on unadapted dialects (version-dependent capability).
            return True

    def _build_generated_column_spec(self, spec: "GeneratedColumnSpec") -> Optional[Any]:
        """Translate a ``GeneratedColumnSpec`` to a column patch.

        Requires generated-column support; otherwise returns ``None``
        (silently ignored).
        """
        if not self._supports_capability("supports_generated_columns"):
            return None
        from ...expression.statements import GeneratedColumnType

        expression = self._resolve_predicate(spec.expression)
        generated_type = (
            GeneratedColumnType.STORED if spec.stored else GeneratedColumnType.VIRTUAL
        )
        return ColumnPatchSpec(
            column=spec.column,
            generated_expression=expression,
            generated_type=generated_type,
        )

    def _build_json_column_spec(self, spec: "JsonColumnSpec") -> Optional[Any]:
        """Translate a ``JsonColumnSpec`` to a column patch using the portable
        ``JsonType``, which each backend renders natively (MySQL ``JSON``,
        PostgreSQL ``JSON``) or as a text fallback (SQLite ``TEXT``)."""
        from ...expression.types import JsonType

        return ColumnPatchSpec(column=spec.column, patched_data_type=JsonType(self))

    def _build_column_type_spec(self, spec: "ColumnTypeSpec") -> Optional[Any]:
        """Default translation for other column-type Specs is ``None`` (unclaimed);
        backends override to provide a native type."""
        return None