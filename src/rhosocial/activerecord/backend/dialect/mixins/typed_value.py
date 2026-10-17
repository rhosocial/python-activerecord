# src/rhosocial/activerecord/backend/dialect/mixins/typed_value.py
"""Dialect rendering for the typed value nodes (``expression.values``).

One method per value type, named for the type, so a backend overrides exactly
the kinds it spells differently. Two strategies live behind that split
(spec 4.4):

* a **data position** (``inline_params = False``) emits a placeholder and hands
  the host value to the driver -- no conversion here, because the driver binds
  ``bytes``, ``date``, ``Decimal`` natively and spec 4.4 puts bind-time
  conversion in the driver adapter's hands;
* a **DDL syntax position** (``inline_params = True``) cannot bind at all, so
  the dialect builds the literal text.

The inline grammars come in the three tiers spec 4.4 requires, in this order:

1. **built in here** -- forms that are the same across backends or differ only
   in spelling: NULL, booleans, numbers, strings, and dates. These delegate to
   :meth:`SQLDialectBase.format_literal`, which already implements the tiering
   and owns the escape helper; spelling a value a second time here would only
   let the two drift apart;
2. **the backend must override** -- forms whose shape is the backend's own:
   binary (``X'...'`` vs ``'\\x...'::bytea``), UUID, INTERVAL, JSON. These
   raise :class:`NotImplementedError` here rather than guessing, and a
   ``str()`` fallback is exactly what the spec forbids;
3. a **protocol on the value** -- for user-defined and backend-specific types
   (PostgreSQL ``Point``, ``inet``, ...), implemented by whoever defines the
   type.

Tier 1 deliberately has no shared "render anything" helper: a generic one would
be the万能入口 spec 4.2 forbids, since it would have to branch on the value's
type and then on the dialect all over again.
"""

from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from ...expression.values import TypedValue


class TypedValueMixin:
    """Formats the ``expression.values`` nodes.

    Every ``format_*_value`` method reads :attr:`inline_params` off the node's
    **class** and takes one of two paths. A backend that needs a different
    literal shape overrides only the methods it disagrees with.
    """

    # -- strategy ---------------------------------------------------------
    #
    # Both paths are single lines of real work; they are spelled out per type
    # because "how does this backend write a binary literal" is a question with
    # eleven answers and must stay answerable one kind at a time.

    def _bind_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A placeholder plus the host value, for a data position."""
        return self.get_parameter_placeholder(), (expr.value,)

    def format_null_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """NULL. One form everywhere: it is a keyword, not a value."""
        if type(expr).inline_params:
            return self.format_literal(None), ()
        return self._bind_value(expr)

    def format_boolean_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A boolean. The spelling is the backend's (``TRUE``/``1``)."""
        if type(expr).inline_params:
            return self.format_literal(expr.value), ()
        return self._bind_value(expr)

    def format_integer_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """An integer, as numeric text."""
        if type(expr).inline_params:
            return self.format_literal(expr.value), ()
        return self._bind_value(expr)

    def format_float_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A double, as numeric text."""
        if type(expr).inline_params:
            return self.format_literal(expr.value), ()
        return self._bind_value(expr)

    def format_decimal_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """An exact decimal, as unquoted numeric text.

        ``format_literal`` renders a ``Decimal`` as ``str(value)`` -- the
        shortest faithful form, unquoted, which is the same text the artifact
        carries as a string (wire §5). Passing it through as ``str`` here would
        make it a *string* literal instead, so the value is handed over whole.
        """
        if type(expr).inline_params:
            return self.format_literal(expr.value), ()
        return self._bind_value(expr)

    def format_string_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A string, quoted with doubled single quotes."""
        if type(expr).inline_params:
            return self.format_literal(expr.value), ()
        return self._bind_value(expr)

    def format_date_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A date as its quoted ISO 8601 text.

        Tier 1 covers this because a quoted ``YYYY-MM-DD`` is what the lenient
        backends accept verbatim. A backend that needs a type prefix or a parse
        call -- Oracle's ``TO_DATE(...)``, say -- overrides this one method.
        """
        if type(expr).inline_params:
            return self.format_literal(expr.value), ()
        return self._bind_value(expr)

    def format_time_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A time of day as its quoted ISO 8601 text."""
        if type(expr).inline_params:
            return self.format_literal(expr.value), ()
        return self._bind_value(expr)

    def format_timestamp_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A date-time as its quoted ISO 8601 text, offset included if aware.

        The offset a naive value does not have is kept, and none is invented:
        ``format_literal`` formats the value the host holds, so a naive
        timestamp stays naive all the way into the SQL text.
        """
        if type(expr).inline_params:
            return self.format_literal(expr.value), ()
        return self._bind_value(expr)

    # -- tier 2: the backend must implement these --------------------------

    def format_binary_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A binary literal. **The backend must implement this.**

        The shape is the backend's own and the base must not guess it:
        SQLite ``X'0102'``, PostgreSQL ``'\\x0102'::bytea``, MySQL ``X'0102'``,
        SQL Server ``0x0102``. A backend that leaves this alone fails loudly at
        the DDL position instead of writing a quoted string where a BLOB
        belongs.
        """
        if not type(expr).inline_params:
            return self._bind_value(expr)
        raise NotImplementedError(
            f"{type(self).__name__} does not implement binary literals; "
            "a DDL position cannot bind, so the backend must override "
            "format_binary_value (spec 4.4 tier 2)"
        )

    def format_uuid_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """A UUID literal. **The backend must implement this.**

        PostgreSQL wants ``'...'::uuid``; the others accept the bare quoted
        text. Guessing here would produce SQL that runs on nine backends and
        fails on one, which is the failure mode the spec's tiering exists to
        prevent.
        """
        if not type(expr).inline_params:
            return self._bind_value(expr)
        raise NotImplementedError(
            f"{type(self).__name__} does not implement UUID literals; "
            "override format_uuid_value (spec 4.4 tier 2)"
        )

    def format_interval_value(self, expr: "TypedValue") -> Tuple[str, tuple]:
        """An INTERVAL literal. **The backend must implement this.**

        ``timedelta`` says how many days, seconds and microseconds; how to
        spell that is the backend's (``INTERVAL '1 2'``, ``'1 day 2 sec'``,
        BigQuery's ``INTERVAL 1 DAY``), and a calendar span cannot be derived
        from a ``timedelta`` at all.
        """
        if not type(expr).inline_params:
            return self._bind_value(expr)
        raise NotImplementedError(
            f"{type(self).__name__} does not implement INTERVAL literals; "
            "override format_interval_value (spec 4.4 tier 2)"
        )
