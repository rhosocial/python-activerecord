# src/rhosocial/activerecord/backend/impl/sqlite/mixins/typed_value.py
"""SQLite's spellings for the value types whose literal form is its own.

SQLite agrees with the base on NULL, booleans, numbers, strings and dates, so
nothing is overridden for those. Two value types differ, and both differ
because SQLite's grammar says so rather than because SQLite is unusual:

* **binary** -- ``X'0102FF'``, the blob-literal form from SQLite's
  ``literal-value`` grammar. Quoting the bytes as text would produce a string
  that reads back as text, which is the wrong value in a ``BLOB`` column and
  the wrong length besides.
* **UUID** -- the bare quoted text. SQLite has no UUID type, and its
  ``TEXT`` columns hold the canonical form as-is; a ``::uuid`` suffix would
  not parse.

**INTERVAL stays unimplemented on purpose.** SQLite has no interval type and
no interval literal, so the base's explicit failure is the right answer: a
DDL position that needs one cannot be written for this engine. That is the
same fail-closed choice the dialect makes for sequences and identity columns,
and it is why this mixin defines no ``format_interval_value`` -- leaving the
method absent is what makes the absence structural.
"""

from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.values import TypedValue


class SQLiteTypedValueMixin:
    """SQLite's tier-2 value literals.

    Stands alone rather than inheriting :class:`TypedValueMixin`, like every
    other SQLite mixin: the dialect composes the specific mixin ahead of the
    generic one, and these two methods win by that position. Inheriting would
    put the base ahead of the other generic mixins and make the ordering the
    dialect has to reason about depend on this class instead.
    """

    def format_binary_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A blob literal: ``X'0102FF'``, uppercase hex.

        Rendered from the bytes rather than from the base64 spelling the
        artifact carries, which is why the node holds ``bytes`` in the first
        place: this conversion has to happen somewhere, and a dialect is the
        only layer that knows which of the two forms its engine accepts.
        """
        if not type(expr).inline_params:
            return self._bind_value(expr)
        return f"X'{bytes(expr.value).hex().upper()}'", ()

    def format_uuid_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A UUID as quoted text -- all SQLite has is a ``TEXT`` column."""
        if not type(expr).inline_params:
            return self._bind_value(expr)
        return self.format_literal(str(expr.value)), ()
