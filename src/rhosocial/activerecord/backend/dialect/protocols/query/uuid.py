# src/rhosocial/activerecord/backend/dialect/protocols/query/uuid.py
"""UUIDSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Protocol, TYPE_CHECKING, Tuple, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.uuid import (
        UUIDCastExpression,
        UUIDConstantExpression,
        UUIDGenerationExpression,
    )


@runtime_checkable
class UUIDSupport(Protocol):
    """Protocol for UUID value operations.

    Storage of a UUID is a separate concern: it belongs to ``DataType`` and
    ``format_data_type_*``, and no member of this protocol reads it. A dialect
    may support generation without a native UUID type, and vice versa.

    Each operation is reported independently, because backends differ
    sharply — a handful have all three, some have generation only, and SQLite
    has none of them (it generates UUIDs in Python).
    """

    def supports_uuid_generation(self) -> bool:
        """Whether the database can produce a UUID on its own.

        False means :class:`UUIDGenerationExpression` raises
        ``UnsupportedFeatureError`` at render time, with a suggestion to
        generate the value in Python.
        """
        ...  # pragma: no cover

    def supports_uuid_constant(self) -> bool:
        """Whether the nil / max UUID constants are available as SQL."""
        ...  # pragma: no cover

    def supports_uuid_cast(self) -> bool:
        """Whether text can be converted to a UUID in SQL.

        Backends disagree on whether malformed input raises, so a dialect that
        implements this must document its behaviour.
        """
        ...  # pragma: no cover

    def format_uuid_generation(self, expr: "UUIDGenerationExpression") -> Tuple[str, Tuple]:
        """Render a fresh-UUID expression.

        Args:
            expr: UUIDGenerationExpression node.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_uuid_constant(self, expr: "UUIDConstantExpression") -> Tuple[str, Tuple]:
        """Render the nil or max UUID constant.

        Args:
            expr: UUIDConstantExpression node.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_uuid_cast(self, expr: "UUIDCastExpression") -> Tuple[str, Tuple]:
        """Render a text-to-UUID conversion.

        Args:
            expr: UUIDCastExpression node.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover