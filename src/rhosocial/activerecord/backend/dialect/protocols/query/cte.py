# src/rhosocial/activerecord/backend/dialect/protocols/ctesupport.py
"""CTESupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Protocol, runtime_checkable

@runtime_checkable
class CTESupport(Protocol):
    """Protocol for Common Table Expression (CTE) support."""

    def supports_basic_cte(self) -> bool:
        """Whether basic CTEs are supported."""
        ...  # pragma: no cover

    def supports_recursive_cte(self) -> bool:
        """Whether recursive CTEs are supported."""
        ...  # pragma: no cover

    def supports_materialized_cte(self) -> bool:
        """Whether MATERIALIZED hint is supported."""
        ...  # pragma: no cover

    def supports_unconditional_cte_order_by(self) -> bool:
        """Whether ORDER BY is allowed unconditionally inside CTE definitions.

        SQL Server prohibits ORDER BY in CTEs unless accompanied by
        TOP, OFFSET, or FOR XML. Most other backends support it.
        """
        ...  # pragma: no cover
