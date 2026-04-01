# src/rhosocial/activerecord/backend/explain/backend_mixin.py
"""
Sync/async backend mixins for EXPLAIN support.

Architecture
------------
_ExplainMixinBase
    Shared non-I/O logic:
    - _build_explain_sql(): wraps the given expression in ExplainExpression
      and calls to_sql() via the dialect.
    - _parse_explain_result(): hook for concrete backends to return a
      specialised ExplainResult subclass (default: BaseExplainResult).

SyncExplainBackendMixin(_ExplainMixinBase)
    Synchronous explain() — calls self.fetch_all() directly.

AsyncExplainBackendMixin(_ExplainMixinBase)
    Asynchronous explain() — awaits self.fetch_all().

Usage
-----
Sync backend::

    class MySyncBackend(SyncExplainBackendMixin, StorageBackend):
        def _parse_explain_result(self, raw_rows, sql, duration):
            rows = [MyRow(**r) for r in raw_rows]
            return MyExplainResult(raw_rows=raw_rows, sql=sql,
                                   duration=duration, rows=rows)

Async backend::

    class MyAsyncBackend(AsyncExplainBackendMixin, AsyncStorageBackend):
        def _parse_explain_result(self, raw_rows, sql, duration):
            ...
"""

import time
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from .types import BaseExplainResult

if TYPE_CHECKING:  # pragma: no cover
    from ..expression.bases import BaseExpression
    from ..expression.statements import ExplainOptions


class _ExplainMixinBase:
    """Shared non-I/O helpers for EXPLAIN backend mixins.

    Both SyncExplainBackendMixin and AsyncExplainBackendMixin inherit from
    this class to share _build_explain_sql() and _parse_explain_result().
    Do not use this class directly.
    """

    # ------------------------------------------------------------------
    # SQL construction (no I/O)
    # ------------------------------------------------------------------

    def _build_explain_sql(
        self,
        expression: "BaseExpression",
        options: Optional["ExplainOptions"] = None,
    ) -> Tuple[str, tuple]:
        """Wrap *expression* in an ExplainExpression and return (sql, params).

        Args:
            expression: The statement to be explained.
            options:    Optional ExplainOptions.

        Returns:
            A (sql_string, params_tuple) pair ready to pass to execute().
        """
        from ..expression.statements import ExplainExpression
        explain_expr = ExplainExpression(self.dialect, expression, options)  # type: ignore[attr-defined]
        return explain_expr.to_sql()

    # ------------------------------------------------------------------
    # Result parsing hook
    # ------------------------------------------------------------------

    def _parse_explain_result(
        self,
        raw_rows: List[Dict[str, Any]],
        sql: str,
        duration: float,
    ) -> BaseExplainResult:
        """Parse raw fetch_all() rows into a structured result object.

        The default implementation returns a plain BaseExplainResult.
        Concrete backends should override this method to return a more
        specific subclass with typed ``rows`` and backend-specific fields.

        Args:
            raw_rows: List of dicts returned by fetch_all().
            sql:      The EXPLAIN SQL that was executed.
            duration: Elapsed time in seconds.

        Returns:
            A BaseExplainResult (or subclass) instance.
        """
        return BaseExplainResult(raw_rows=raw_rows, sql=sql, duration=duration)


class SyncExplainBackendMixin(_ExplainMixinBase):
    """Mixin that adds synchronous explain() to a StorageBackend subclass.

    Mix this in before StorageBackend in the MRO and override
    _parse_explain_result() to return a backend-specific result type.

    Example::

        class MyBackend(SyncExplainBackendMixin, StorageBackend):
            def _parse_explain_result(self, raw_rows, sql, duration):
                rows = [MyRow(**r) for r in raw_rows]
                return MyExplainResult(raw_rows=raw_rows, sql=sql,
                                       duration=duration, rows=rows)
    """

    def explain(
        self,
        expression: "BaseExpression",
        options: Optional["ExplainOptions"] = None,
    ) -> BaseExplainResult:
        """Execute EXPLAIN *expression* synchronously.

        Args:
            expression: Any BaseExpression except ExplainExpression itself.
            options:    Optional ExplainOptions.

        Returns:
            A BaseExplainResult subclass determined by _parse_explain_result().
        """
        sql, params = self._build_explain_sql(expression, options)
        start = time.perf_counter()
        raw_rows = self.fetch_all(sql, params)  # type: ignore[attr-defined]
        duration = time.perf_counter() - start
        return self._parse_explain_result(raw_rows, sql, duration)


class AsyncExplainBackendMixin(_ExplainMixinBase):
    """Mixin that adds asynchronous explain() to an AsyncStorageBackend subclass.

    Mix this in before AsyncStorageBackend in the MRO and override
    _parse_explain_result() to return a backend-specific result type.

    Example::

        class MyAsyncBackend(AsyncExplainBackendMixin, AsyncStorageBackend):
            def _parse_explain_result(self, raw_rows, sql, duration):
                rows = [MyRow(**r) for r in raw_rows]
                return MyExplainResult(raw_rows=raw_rows, sql=sql,
                                       duration=duration, rows=rows)
    """

    async def explain(
        self,
        expression: "BaseExpression",
        options: Optional["ExplainOptions"] = None,
    ) -> BaseExplainResult:
        """Execute EXPLAIN *expression* asynchronously.

        Args:
            expression: Any BaseExpression except ExplainExpression itself.
            options:    Optional ExplainOptions.

        Returns:
            A BaseExplainResult subclass determined by _parse_explain_result().
        """
        sql, params = self._build_explain_sql(expression, options)
        start = time.perf_counter()
        raw_rows = await self.fetch_all(sql, params)  # type: ignore[attr-defined]
        duration = time.perf_counter() - start
        return self._parse_explain_result(raw_rows, sql, duration)
