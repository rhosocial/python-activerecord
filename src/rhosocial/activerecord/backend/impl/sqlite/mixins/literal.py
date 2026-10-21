# src/rhosocial/activerecord/backend/impl/sqlite/mixins/literal.py
"""SQLite's tier-2 value literals.

``SQLDialectBase.format_literal`` is the single entry point for writing a value
as SQL text, and it resolves in three tiers: the portable scalars it knows, the
types a backend spells for itself, and the literal-construction protocol. This
module is SQLite's second tier. SQLite has two such types and no more:

* ``bytes`` becomes a blob literal, ``X'0102FF'`` with uppercase hex. It is
  rendered from the bytes rather than from the base64 spelling an artifact
  carries, which is why a node holds ``bytes`` in the first place.
* ``UUID`` becomes quoted text, because all SQLite has is a ``TEXT`` column.

Everything else falls through to the base implementation, which is where the
portable forms and the protocol live. Nothing here is SQLite-specific except
the two spellings above.
"""

import uuid
from typing import Any


class LiteralValueMixin:
    """SQLite's tier-2 branches of :meth:`format_literal`."""

    def format_literal(self, value: Any) -> str:
        """Render *value* as inline SQL text, SQLite's spelling where it has one.

        Args:
            value: The host value to write into the statement.

        Returns:
            The escaped literal text, without a bind parameter.

        Raises:
            TypeError: The base implementation refuses a type SQLite has no
                literal form for, and this is the same refusal.
        """
        if isinstance(value, (bytes, bytearray)):
            return f"X'{bytes(value).hex().upper()}'"
        if isinstance(value, uuid.UUID):
            return self.format_literal(str(value))
        return super().format_literal(value)