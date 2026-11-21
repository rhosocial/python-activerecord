# src/rhosocial/activerecord/migration/context.py
"""Execution context passed to a user migration's ``up(ctx)`` / ``down(ctx)``.

The context is the bridge between a migration and the backend: it exposes the
backend-suggestion "how-to" answers as ordinary methods, and a single
``apply()`` that either executes the expressions (real run) or only renders them
(dry run). It never touches the backend migration runtime system.
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence, TYPE_CHECKING

from ..backend.suggestion import PartitionSuggestionRenderer

if TYPE_CHECKING:  # pragma: no cover
    from ..backend.base import StorageBackend
    from ..backend.expression.bases import BaseExpression
    from ..backend.expression.statements import PartitionStrategy


class _SuggestionMixin:
    """Backend-suggestion accessors, shared by sync and async contexts.

    Each accessor delegates to an OO renderer. Returns ``None`` when the backend
    has no answer (no suggestion support, explicit unsupported, or a no-op). The
    caller can check ``None`` and skip, or pass straight to ``apply`` (which
    ignores None).
    """

    _renderer = PartitionSuggestionRenderer()

    def _suggest(
        self, intent: str, strategy: "PartitionStrategy", plan: object
    ) -> Optional[List["BaseExpression"]]:
        return self._renderer.parts(self.backend, intent, strategy, plan)

    def suggest_partition_build(self, strategy: "PartitionStrategy", plan: object):
        return self._suggest("build", strategy, plan)

    def suggest_partition_table_drop(self, strategy: "PartitionStrategy", plan: object):
        return self._suggest("table_drop", strategy, plan)

    def suggest_partition_table_alter(self, strategy: "PartitionStrategy", plan: object):
        return self._suggest("table_alter", strategy, plan)

    def suggest_partition_add(self, strategy: "PartitionStrategy", plan: object):
        return self._suggest("add", strategy, plan)

    def suggest_partition_drop(self, strategy: "PartitionStrategy", plan: object):
        return self._suggest("drop", strategy, plan)

    def suggest_partition_split(self, strategy: "PartitionStrategy", plan: object):
        return self._suggest("split", strategy, plan)

    def suggest_partition_merge(self, strategy: "PartitionStrategy", plan: object):
        return self._suggest("merge", strategy, plan)

    def suggest_partition_retention(self, strategy: "PartitionStrategy", plan: object):
        return self._suggest("retention", strategy, plan)


class _ContextBase(_SuggestionMixin):
    def __init__(
        self,
        backend: "StorageBackend",
        *,
        direction: str = "up",
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
