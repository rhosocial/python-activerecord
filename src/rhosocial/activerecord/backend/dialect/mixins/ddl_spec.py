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
    DDLSpec,
    ForeignKeySpec,
    IndexSpec,
    UniqueSpec,
)
from ...expression.statements.ddl_table import (
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
        if isinstance(spec, ForeignKeySpec):
            return self._build_foreign_key_spec(spec)
        if isinstance(spec, IndexSpec):
            return self._build_index_spec(spec)
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
        return None