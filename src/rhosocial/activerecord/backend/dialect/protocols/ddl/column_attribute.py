# src/rhosocial/activerecord/backend/dialect/protocols/ddl/column_attribute.py
"""ColumnAttributeSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Any, Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements.ddl_table import ColumnClause


@runtime_checkable
class ColumnAttributeSupport(Protocol):
    """Protocol for rendering explicitly supplied column attributes."""

    def format_column_attribute(self, expr: "ColumnClause") -> "Tuple[str, tuple]":
        """Render one selected attribute as a column-definition fragment.

        Args:
            expr: A selected (renderable) column attribute.

        Returns:
            A ``(sql, params)`` tuple with a leading space (DDL accepts no
            bind parameters, so ``params`` is normally empty).
        """
        ...  # pragma: no cover

    def translate_ar_attribute(self, attr: Any) -> Any:
        """DEPRECATED — AR-layer translation now lives in ``base.derivation``.

        Kept on the protocol only for external callers; core no longer uses it
        and it will be removed in a future release. Model declarations are
        translated to expression-layer clauses by the deriver before reaching
        ``ColumnDefinition.attributes``.

        Args:
            attr: An AR-layer ``ColumnAttribute``.

        Returns:
            The expression-layer clause, or ``None`` when this dialect cannot
            render the attribute at all.
        """
        ...  # pragma: no cover
