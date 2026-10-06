# src/rhosocial/activerecord/backend/dialect/protocols/query/locking.py
"""LockingSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.query_parts import ForUpdateClause


@runtime_checkable
class LockingSupport(Protocol):
    """Protocol for row-level locking support (FOR UPDATE, SKIP LOCKED)."""

    def supports_for_update(self) -> bool:
        """Whether the engine accepts the form ``for_update``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def supports_for_update_skip_locked(self) -> bool:
        """Whether FOR UPDATE SKIP LOCKED is supported."""
        ...  # pragma: no cover

    def supports_for_share(self) -> bool:
        """Whether the FOR SHARE lock strength is supported."""
        ...  # pragma: no cover

    def supports_for_no_key_update(self) -> bool:
        """Whether FOR NO KEY UPDATE is supported."""
        ...  # pragma: no cover

    def supports_for_key_share(self) -> bool:
        """Whether FOR KEY SHARE is supported."""
        ...  # pragma: no cover

    def supports_lock_in_share_mode(self) -> bool:
        """Whether the legacy LOCK IN SHARE MODE syntax is supported."""
        ...  # pragma: no cover

    def format_for_update_clause(self, clause: "ForUpdateClause") -> Tuple[str, tuple]:
        """
        Formats a FOR UPDATE clause with optional locking modifiers.

        Args:
            clause: ForUpdateClause object containing locking options

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        ...  # pragma: no cover
