# src/rhosocial/activerecord/migration/context.py
"""Execution context passed to a user migration's ``up(ctx)`` / ``down(ctx)``.

The context is the bridge between a migration and the backend: it exposes the
backend-suggestion "how-to" answers as ordinary methods, and a single
``apply()`` that either executes the expressions (real run) or only renders them
(dry run). It never touches the backend migration runtime system.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from ..backend.dialect.partition_capability import PartitionCapability
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
    from .outcome import PartitionChangeOutcome, SchemaChangeOutcome
    from .schema_change import ChangePlan, ResolvedSuggestion, SuggestionResolution


#: Intent -> the existing raw partition-suggestion accessor on this mixin.
#: Only consulted when the dialect reports ``PartitionCapability.NATIVE``.
_PARTITION_INTENT_RAW: Dict[str, str] = {
    "build": "suggest_partition_build_raw",
    "table_drop": "suggest_partition_table_drop_raw",
    "table_alter": "suggest_partition_table_alter_raw",
    "add": "suggest_partition_add_raw",
    "drop": "suggest_partition_drop_raw",
    "split": "suggest_partition_split_raw",
    "merge": "suggest_partition_merge_raw",
    "retention": "suggest_partition_retention_raw",
}

#: Generic last-line destructive guard. This is *not* backend safety logic:
#: it only recognizes class names and rendered spellings so an outcome cannot
#: smuggle a destructive statement past ``apply_change``. Backends keep their
#: own capability checks; this guard never tries to replace them.
_DESTRUCTIVE_CLASS_NAMES = frozenset(
    {
        "DropTableStatement",
        "DropSchemaStatement",
        "TruncateStatement",
        "DeleteStatement",
    }
)
_DESTRUCTIVE_SQL = (
    (re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE), "DROP TABLE"),
    (re.compile(r"\bDROP\s+SCHEMA\b", re.IGNORECASE), "DROP SCHEMA"),
    (re.compile(r"\bTRUNCATE\b", re.IGNORECASE), "TRUNCATE"),
    (re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE), "DELETE FROM"),
)
#: ``SWITCH ... TO`` moves data between partitions/objects. A bare switch-out
#: is data-affecting; a round trip needs a matching switch back in the chain.
_SWITCH_SQL = re.compile(r"\bSWITCH\b[\s\S]*?\bTO\b", re.IGNORECASE)


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

    # -- User-facing planning -------------------------------------------------

    def plan_schema_change(self, old_model: Any, new_model: Any) -> "SchemaChangeOutcome":
        """Plan a model-declaration change and resolve all of its points.

        One entry point for users who previously had to call ``plan_changes``
        and ``resolve_suggestions`` themselves. The returned outcome carries the
        executable chain plus a grouped account of every suggestion point —
        ``False``, ``None`` and a missing protocol are never silently dropped.
        """
        from .outcome import SchemaChangeOutcome

        plan = self.plan_changes(old_model, new_model)
        resolution = self.resolve_suggestions(plan)
        return SchemaChangeOutcome(
            statements=tuple(plan.statements),
            supported=tuple(resolution.resolved),
            unsupported=tuple(resolution.unsupported),
            no_answer=tuple(resolution.no_answer),
            missing=tuple(resolution.missing),
        )

    def _partition_capability(self) -> PartitionCapability:
        """Read the dialect's partitioning capability, failing closed.

        ``partition_capability()`` is the authoritative three-way answer. A
        dialect that only exposes the older boolean is derived from it; with
        neither, the result is ``UNSUPPORTED`` so no DDL is ever invented for a
        backend whose partitioning model is unknown.
        """
        target = self._suggestion_target()
        getter = getattr(target, "partition_capability", None)
        if callable(getter):
            capability = getter()
            try:
                return PartitionCapability(capability)
            except (TypeError, ValueError):
                return capability
        supports = getattr(target, "supports_table_partitioning", None)
        if callable(supports) and supports() is True:
            return PartitionCapability.NATIVE
        return PartitionCapability.UNSUPPORTED

    def plan_partition_change(
        self, intent: str, strategy: "PartitionByClause", plan: object
    ) -> "PartitionChangeOutcome":
        """Plan one partition lifecycle intent without fabricating DDL.

        The dialect's ``partition_capability()`` is read **first**. ``AUTOMATIC``
        (engine-managed storage) and ``UNSUPPORTED`` (no partitioning) return an
        explicit unaddressable outcome with a report explaining why, and no
        backend partition suggestion is called. Only ``NATIVE`` consults the
        existing ``suggest_partition_*_raw`` accessor, keeping its tri-state
        answer distinct.
        """
        from .outcome import PARTITION_STATE_REASONS, PartitionChangeOutcome

        capability = self._partition_capability()
        if capability is PartitionCapability.AUTOMATIC:
            return PartitionChangeOutcome(
                capability=capability,
                operations=False,
                state="engine-managed",
                intent=intent,
                reason=PARTITION_STATE_REASONS["engine-managed"],
            )
        if capability is not PartitionCapability.NATIVE:
            return PartitionChangeOutcome(
                capability=capability,
                operations=False,
                state="not-supported",
                intent=intent,
                reason=PARTITION_STATE_REASONS["not-supported"],
            )

        try:
            method_name = _PARTITION_INTENT_RAW[intent]
        except KeyError as exc:
            raise ValueError(f"unknown partition change intent: {intent!r}") from exc
        raw = getattr(self, method_name)(strategy, plan)
        if raw.state == "actions":
            operations: Any = tuple(raw.operations)
        elif raw.state == "no-action":
            operations = ()
        else:
            operations = False
        return PartitionChangeOutcome(
            capability=capability,
            operations=operations,
            state=raw.state,
            intent=intent,
            reason=PARTITION_STATE_REASONS.get(raw.state, ""),
        )

    # -- Shared guard for applying an outcome ---------------------------------

    def _prepare_change(
        self,
        outcome: Any,
        *,
        allow_incomplete: bool,
        authorized_destructive: bool,
    ) -> Tuple[List[Any], List[tuple]]:
        """Validate an outcome and return ``(statements, rendered)``.

        Shared by sync and async contexts. It applies only what the outcome
        contains — never the originating ``plan`` or any extra expressions —
        and checks completeness before rendering. Incomplete outcomes,
        destructive statements and multi-action statements are refused here as
        a last-line, backend-neutral safety net.
        """
        from .outcome import PartitionChangeOutcome, SchemaChangeOutcome

        if isinstance(outcome, SchemaChangeOutcome):
            if not outcome.is_complete and not allow_incomplete:
                raise ValueError(
                    "incomplete schema change outcome; pass allow_incomplete=True "
                    "to apply only the resolved statements:\n" + outcome.report()
                )
            statements = [expr for expr in outcome.statements if expr is not None]
        elif isinstance(outcome, PartitionChangeOutcome):
            if outcome.operations is False:
                if not allow_incomplete:
                    raise ValueError(
                        "unaddressable partition change outcome; pass "
                        "allow_incomplete=True to skip it:\n" + outcome.report()
                    )
                statements = []
            else:
                statements = [expr for expr in outcome.operations if expr is not None]
        else:
            raise TypeError(f"unsupported change outcome type: {type(outcome).__name__}")

        # The 1:1 SQL rule is unconditional: no opt-in bundles several actions.
        for expr in statements:
            actions = getattr(expr, "actions", None)
            if isinstance(actions, (list, tuple)) and len(actions) > 1:
                raise ValueError(
                    f"{type(expr).__name__} carries {len(actions)} actions; "
                    "one expression must map to exactly one action."
                )

        rendered = self._render(statements)
        if not authorized_destructive:
            for expr in statements:
                if type(expr).__name__ in _DESTRUCTIVE_CLASS_NAMES:
                    raise ValueError(
                        f"refused destructive DDL ({type(expr).__name__}); pass "
                        "authorized_destructive=True to allow it."
                    )
            sqls = [sql for sql, _ in rendered]
            switches = [sql for sql in sqls if _SWITCH_SQL.search(sql)]
            if switches and len(switches) < 2:
                raise ValueError(
                    "refused data-moving SWITCH ... TO without a matching switch "
                    "back; pass authorized_destructive=True to allow it."
                )
            for sql in sqls:
                for pattern, label in _DESTRUCTIVE_SQL:
                    if pattern.search(sql):
                        raise ValueError(
                            f"refused destructive DDL ({label}); pass "
                            "authorized_destructive=True to allow it."
                        )
        return statements, rendered

    def _execute_rendered(self, rendered: List[tuple]) -> int:
        """Execute or record already-rendered statements (sync)."""
        from ..backend.options import ExecutionOptions
        from ..backend.schema import StatementType

        if self.dry_run:
            self.dry_run_sql.extend(rendered)
            return len(rendered)
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        for sql, params in rendered:
            self.backend.execute(sql, params, options=options)
        return len(rendered)

    async def _execute_rendered_async(self, rendered: List[tuple]) -> int:
        """Execute or record already-rendered statements (async)."""
        from ..backend.options import ExecutionOptions
        from ..backend.schema import StatementType

        if self.dry_run:
            self.dry_run_sql.extend(rendered)
            return len(rendered)
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        for sql, params in rendered:
            await self.backend.execute(sql, params, options=options)
        return len(rendered)


class MigrationContext(_ContextBase):
    """Synchronous migration context."""

    def apply(self, *expressions: Any) -> int:
        """Execute expressions, or only render them under dry-run.

        Accepts a single list/tuple (so a suggestion's result can be passed
        directly), or individual expressions. ``None`` entries are ignored.
        Returns the number of statements applied/rendered.
        """
        flat: List[Any] = []
        for expr in expressions:
            if isinstance(expr, (list, tuple)):
                flat.extend(e for e in expr if e is not None)
            elif expr is not None:
                flat.append(expr)
        return self._execute_rendered(self._render(flat))

    def apply_change(
        self,
        outcome: Any,
        *,
        allow_incomplete: bool = False,
        authorized_destructive: bool = False,
    ) -> int:
        """Apply only the executable chain carried by *outcome*.

        Refuses incomplete outcomes, destructive DDL and multi-action
        statements unless the matching explicit opt-in is passed. See
        :meth:`_prepare_change` for the shared guard.
        """
        _, rendered = self._prepare_change(
            outcome,
            allow_incomplete=allow_incomplete,
            authorized_destructive=authorized_destructive,
        )
        return self._execute_rendered(rendered)


class AsyncMigrationContext(_ContextBase):
    """Asynchronous migration context (parity with MigrationContext)."""

    async def apply(self, *expressions: Any) -> int:
        flat: List[Any] = []
        for expr in expressions:
            if isinstance(expr, (list, tuple)):
                flat.extend(e for e in expr if e is not None)
            elif expr is not None:
                flat.append(expr)
        return await self._execute_rendered_async(self._render(flat))

    async def apply_change(
        self,
        outcome: Any,
        *,
        allow_incomplete: bool = False,
        authorized_destructive: bool = False,
    ) -> int:
        """Async parity of :meth:`MigrationContext.apply_change`."""
        _, rendered = self._prepare_change(
            outcome,
            allow_incomplete=allow_incomplete,
            authorized_destructive=authorized_destructive,
        )
        return await self._execute_rendered_async(rendered)
