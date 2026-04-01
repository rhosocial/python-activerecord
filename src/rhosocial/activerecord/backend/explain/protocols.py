# src/rhosocial/activerecord/backend/explain/protocols.py
"""
Sync/async backend protocols for EXPLAIN support.

Following the project's sync/async parity principle, the two protocols are
completely independent — a sync backend implements SyncExplainBackendProtocol
and an async backend implements AsyncExplainBackendProtocol.  Neither inherits
from the other.
"""

from typing import Optional, TYPE_CHECKING
from typing_extensions import Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from ..expression.bases import BaseExpression
    from ..expression.statements import ExplainOptions
    from .types import BaseExplainResult


@runtime_checkable
class SyncExplainBackendProtocol(Protocol):
    """Protocol for synchronous backends that support EXPLAIN.

    A backend that mixes in SyncExplainBackendMixin automatically satisfies
    this protocol.  Third-party backends may implement explain() directly
    without using the mixin.
    """

    def explain(
        self,
        expression: "BaseExpression",
        options: Optional["ExplainOptions"] = None,
    ) -> "BaseExplainResult":
        """Execute EXPLAIN for *expression* and return a structured result.

        Args:
            expression: Any BaseExpression except ExplainExpression itself
                        (e.g. QueryExpression, InsertExpression).
            options:    Optional ExplainOptions controlling the EXPLAIN mode
                        and output format.

        Returns:
            A BaseExplainResult subclass whose concrete type depends on the
            backend implementation.
        """
        ...


@runtime_checkable
class AsyncExplainBackendProtocol(Protocol):
    """Protocol for asynchronous backends that support EXPLAIN.

    A backend that mixes in AsyncExplainBackendMixin automatically satisfies
    this protocol.
    """

    async def explain(
        self,
        expression: "BaseExpression",
        options: Optional["ExplainOptions"] = None,
    ) -> "BaseExplainResult":
        """Asynchronously execute EXPLAIN for *expression*.

        Args and returns: see SyncExplainBackendProtocol.explain().
        """
        ...
