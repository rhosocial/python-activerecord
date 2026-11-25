# src/rhosocial/activerecord/migration/context.py
"""Execution context passed to a user migration's ``up(ctx)`` / ``down(ctx)``.

The context is the bridge between a migration and the backend: it exposes the
backend-suggestion "how-to" answers as ordinary methods, and a single
``apply()`` that either executes the expressions (real run) or only renders them
(dry run). It never touches the backend migration runtime system.
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence, TYPE_CHECKING

from ..base.derivation import partition_suggestion_operations, partition_suggestion_outcome
from .core import DEFAULT_DIRECTION

if TYPE_CHECKING:  # pragma: no cover
    from ..backend.base import StorageBackend
    from ..backend.expression.bases import BaseExpression
    from ..backend.expression.statements import PartitionByClause
    from ..backend.suggestion.definitions import (
        ColumnReorderSuggestion,
        PartitionSchemeChangeSuggestion,
        TableConstraintChangeSuggestion,
        TableIndexChangeSuggestion,
    )
    from ..backend.suggestion.definitions.change_plan import SuggestionPoint
    from .schema_change import ChangePlan, ResolvedSuggestion, SuggestionResolution


class _SuggestionMixin:
    """Backend-suggestion accessors, shared by sync and async contexts.

    Each ``suggest_partition_*`` accessor reads a backend suggestion value's
    expression chain. Returns ``None`` when the backend has no answer (no
    suggestion support, explicit unsupported, or a no-op) — the historical,
    convenience behaviour; ``apply`` ignores ``None``.

    Each ``suggest_partition_*_raw`` counterpart returns the full
    ``PartitionSuggestionOutcome`` instead, keeping "explicitly unsupported"
    distinct from "no action", for callers that must report that difference.

    The four ``suggest_*`` change accessors return a ``ResolvedSuggestion``:
    a tri-state answer (actions / explicit unsupported / no answer / missing
    protocol) that never collapses ``False`` into ``None``.
    """

    def _suggestion_target(self):
        """The object carrying partition-suggestion protocols.

        Suggestion protocols live on the dialect, but a lightweight backend
        double in tests may carry them directly. Prefer the dialect when the
        backend exposes one; fall back to the backend itself otherwise.
        """
        return getattr(self.backend, "dialect", self.backend)

    def _suggest(
        self, intent: str, strategy: "PartitionByClause", plan: object
    ) -> Optional[List["BaseExpression"]]:
        return partition_suggestion_operations(self._suggestion_target(), intent, strategy, plan)

    def _outcome(self, intent: str, strategy: "PartitionByClause", plan: object):
        return partition_suggestion_outcome(self._suggestion_target(), intent, strategy, plan)

    def suggest_partition_build(self, strategy: "PartitionByClause", plan: object):
        return self._suggest("build", strategy, plan)

    def suggest_partition_build_raw(self, strategy: "PartitionByClause", plan: object):
        return self._outcome("build", strategy, plan)

    def suggest_partition_table_drop(self, strategy: "PartitionByClause", plan: object):
        return self._suggest("table_drop", strategy, plan)

    def suggest_partition_table_drop_raw(self, strategy: "PartitionByClause", plan: object):
        return self._outcome("table_drop", strategy, plan)

    def suggest_partition_table_alter(self, strategy: "PartitionByClause", plan: object):
        return self._suggest("table_alter", strategy, plan)

    def suggest_partition_table_alter_raw(self, strategy: "PartitionByClause", plan: object):
        return self._outcome("table_alter", strategy, plan)

    def suggest_partition_add(self, strategy: "PartitionByClause", plan: object):
        return self._suggest("add", strategy, plan)

    def suggest_partition_add_raw(self, strategy: "PartitionByClause", plan: object):
        return self._outcome("add", strategy, plan)

    def suggest_partition_drop(self, strategy: "PartitionByClause", plan: object):
        return self._suggest("drop", strategy, plan)

    def suggest_partition_drop_raw(self, strategy: "PartitionByClause", plan: object):
        return self._outcome("drop", strategy, plan)

    def suggest_partition_split(self, strategy: "PartitionByClause", plan: object):
        return self._suggest("split", strategy, plan)

    def suggest_partition_split_raw(self, strategy: "PartitionByClause", plan: object):
        return self._outcome("split", strategy, plan)

    def suggest_partition_merge(self, strategy: "PartitionByClause", plan: object):
        return self._suggest("merge", strategy, plan)

    def suggest_partition_merge_raw(self, strategy: "PartitionByClause", plan: object):
        return self._outcome("merge", strategy, plan)

    def suggest_partition_retention(self, strategy: "PartitionByClause", plan: object):
        return self._suggest("retention", strategy, plan)

    def suggest_partition_retention_raw(self, strategy: "PartitionByClause", plan: object):
        return self._outcome("retention", strategy, plan)

    def _change_suggestion(self, point: "SuggestionPoint") -> "ResolvedSuggestion":
        """Consume one frozen change point against the suggestion target."""
        from .schema_change import resolve_point

        return resolve_point(point, self._suggestion_target())

    def suggest_column_reorder(self, point: "ColumnReorderSuggestion") -> "ResolvedSuggestion":
        return self._change_suggestion(point)

    def suggest_table_constraint_change(
        self, point: "TableConstraintChangeSuggestion"
    ) -> "ResolvedSuggestion":
        return self._change_suggestion(point)

    def suggest_table_index_change(self, point: "TableIndexChangeSuggestion") -> "ResolvedSuggestion":
        return self._change_suggestion(point)

    def suggest_partition_scheme_change(
        self, point: "PartitionSchemeChangeSuggestion"
    ) -> "ResolvedSuggestion":
        return self._change_suggestion(point)


class _ContextBase(_SuggestionMixin):
    def __init__(
        self,
        backend: "StorageBackend",
        *,
        direction: str = DEFAULT_DIRECTION,
        version: str = "",
        dry_run: bool = False,
    ):
        self.backend = backend
        self.direction = direction
        self.version = version
        self.dry_run = dry_run
        self.dry_run_sql: List[tuple] = []

    @property
    def is_up(self) -> bool:
        return self.direction == "up"

    @property
    def is_down(self) -> bool:
        return self.direction == "down"

    def _render(self, expressions: Sequence[Any]) -> List[tuple]:
        rendered = []
        for expr in expressions:
            if expr is None:
                continue
            sql, params = expr.to_sql()
            rendered.append((sql, params))
        return rendered

    def plan_changes(self, old_model: Any, new_model: Any) -> Any:
        """Plan the schema change from *old_model* to *new_model*.

        Returns a ``ChangePlan`` whose ``statements`` are core ALTER expressions
        ready for :meth:`apply`::

            ctx.apply(*ctx.plan_changes(User20261124, User).statements)

        Single-action changes are emitted directly (expression–dialect system,
        layer-separation A1). Multi-step changes appear in
        ``plan.suggestion_points`` for the user to resolve via a backend
        suggestion — this module never hard-codes a backend strategy.
        """
        from .schema_change import plan_changes as _plan

        return _plan(old_model, new_model, self._suggestion_target())

    def resolve_suggestions(self, plan: "ChangePlan") -> "SuggestionResolution":
        """Explicitly resolve *plan*'s frozen suggestion points.

        ``plan_changes`` is unchanged; this is a separate, caller-invoked step.
        Actionable expressions are appended to ``plan.statements`` so a migration
        can apply them with ``ctx.apply(*plan.statements)``. The returned report
        keeps "unsupported" / "no-answer" / "missing-protocol" distinct, so a
        ``False`` answer is never silently dropped.
        """
        from .schema_change import resolve_suggestions as _resolve

        return _resolve(plan, self._suggestion_target())


class MigrationContext(_ContextBase):
    """Synchronous migration context."""

    def apply(self, *expressions: Any) -> int:
        """Execute expressions, or only render them under dry-run.

        Accepts a single list/tuple (so a suggestion's result can be passed
        directly), or individual expressions. ``None`` entries are ignored.
        Returns the number of statements applied/rendered.
        """
        from ..backend.options import ExecutionOptions
        from ..backend.schema import StatementType

        flat: List[Any] = []
        for expr in expressions:
            if isinstance(expr, (list, tuple)):
                flat.extend(e for e in expr if e is not None)
            elif expr is not None:
                flat.append(expr)
        rendered = self._render(flat)
        if self.dry_run:
            self.dry_run_sql.extend(rendered)
            return len(rendered)
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        for sql, params in rendered:
            self.backend.execute(sql, params, options=options)
        return len(rendered)


class AsyncMigrationContext(_ContextBase):
    """Asynchronous migration context (parity with MigrationContext)."""

    async def apply(self, *expressions: Any) -> int:
        from ..backend.options import ExecutionOptions
        from ..backend.schema import StatementType

        flat: List[Any] = []
        for expr in expressions:
            if isinstance(expr, (list, tuple)):
                flat.extend(e for e in expr if e is not None)
            elif expr is not None:
                flat.append(expr)
        rendered = self._render(flat)
        if self.dry_run:
            self.dry_run_sql.extend(rendered)
            return len(rendered)
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        for sql, params in rendered:
            await self.backend.execute(sql, params, options=options)
        return len(rendered)
