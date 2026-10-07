# src/rhosocial/activerecord/backend/dialect/protocols/ddl/column_attribute.py
"""ColumnAttributeSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....base.ddl import ColumnAttribute


@runtime_checkable
class ColumnAttributeSupport(Protocol):
    """Protocol for rendering explicitly supplied column attributes."""

    def format_column_attribute(self, attr: "ColumnAttribute") -> Tuple[str, tuple]:
        """Render one selected attribute as a column-definition fragment.

        Args:
            attr: A selected (renderable) column attribute.

        Returns:
            A ``(sql, params)`` tuple with a leading space (DDL accepts no
            bind parameters, so ``params`` is normally empty).
        """
        ...  # pragma: no cover
