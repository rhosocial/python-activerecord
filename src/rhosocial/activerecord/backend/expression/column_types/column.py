# src/rhosocial/activerecord/backend/expression/column_types/column.py
from ..column_types.column_types import ColumnBase


class Column(ColumnBase):
    """A column reference whose type is not known: it renders, and that is all.

    This is the **bare** column. Nothing established what it holds, so it
    offers no operation at all — not comparison, not ``LIKE``, not arithmetic.
    The previous shape (the whole operation set, on the theory that offering
    less would be guessing) had the failure the typed classes exist to
    prevent: a caller compared two of them and got Python's *identity*
    answer, silently, instead of SQL. A bare reference that cannot say what
    it holds cannot promise an operation the database will accept either, so
    it promises nothing and the query layer builds its predicates
    explicitly — :class:`~...expression.predicates.predicates.ComparisonPredicate`,
    ``InPredicate``, ``IsNullPredicate`` — which work on any column because
    they ask the *dialect*, not the column, for the SQL.

    Two things lead here:

    * **A string at a public entry point.** ``order_by("name")``,
      ``count("price")`` and ``select("id")`` accept a column name as text.
      The framework has no annotation to consult, so it cannot know what the
      column holds. Pass the model proxy instead, ``order_by(User.c.name)``,
      and the column arrives typed.
    * **A model field whose annotation cannot be classified** (``Any``, an
      unresolvable ``Union``) — the field's operations are unknown, and a
      class that guessed them would be the bug the narrow classes prevent.

    An explicit ``UseColumnType(Column)`` declaration reaches this class too;
    what it says is "render the reference and build predicates elsewhere".
    When the type *is* known,
    :class:`FieldProxy<rhosocial.activerecord.base.field_proxy.FieldProxy>`
    returns the narrow class instead, so ``User.c.age`` is an
    :class:`~...expression.column_types.column_types.IntegerColumn` and offers no
    ``.like()``. The class identity of a typed column does not vary by
    backend; only its storage does.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column"
