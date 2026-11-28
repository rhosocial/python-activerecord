# src/rhosocial/activerecord/backend/expression/value_types/parameter.py
from typing import Any, TYPE_CHECKING

from ..bases.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class Parameter(BaseExpression):
    """A parameter: a value at one position, and the decision how it reaches SQL.

    Every value that reaches SQL passes through this class, so that the question
    "does this value become a bind parameter or SQL text?" has exactly one place
    that answers it. Nothing else in the tree has to know: a formatter calls
    ``child.to_sql()`` and gets ``(sql, params)`` back, whether the child was a
    function call or a value.

    :attr:`inline` is that answer, and it is per **position** rather than per
    class. A node whose values all take the same treatment never needs it — the
    default, ``False``, binds, which is what every DQL/DML data position wants.
    A DDL syntax position that accepts no bind parameters at all passes
    ``inline=True`` and gets escaped SQL text instead. Where one node holds
    several values and only some of them are exempt from binding, this is the
    only way to say so.

    What the class deliberately does **not** claim is what kind of value this
    is. It is not a :class:`~...bases.SQLValue`: that category says "this
    expression yields a value of some type", and a bare position does not know
    its type — ``NULLIF(a, b)`` is text or a number depending on the data. The
    earlier version of this class inherited the comparison, arithmetic and
    string-pattern mixins, which let ``Parameter(d, 7).like()`` compile and
    promised SQL the database would reject. The result's type is declared
    elsewhere, by :meth:`~...mixins.ResultTypeMixin.as_text` and its siblings.

    Nor does it know a **type**: an artifact carries the value as-is, and
    whether ``json.dumps`` can write it is that value type's own contract.

    Nor is a parameter aliasable. A bind parameter has no name to give — the
    parameter the driver fills in is the driver's, not the query's — and a name
    on SQL text would be naming text rather than a result. Aliasing belongs to
    the things that produce a named result, which is what
    :class:`~...bases.SQLValue` is for.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_parameter_expression"

    #: ``None`` is the SQL ``NULL``, so this required parameter may hold it.
    NULLABLE_REQUIRED = frozenset({"value"})

    def __init__(
        self,
        dialect: "SQLDialectBase",
        value: Any,
        *,
        inline: bool = False,
    ):
        super().__init__(dialect)
        self.value = value
        self.inline = inline

    def __repr__(self) -> str:
        where = "" if not self.inline else ", inline"
        return f"Parameter({self.value!r}{where})"
