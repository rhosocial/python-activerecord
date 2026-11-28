# src/rhosocial/activerecord/backend/expression/value_types/logical.py
from typing import Any

from ..bases.bases import SQLValue
from ..bases.mixins import (
    AliasableMixin,
    BooleanLogicMixin,
    ComparisonMixin,
    NotANumberMixin,
    TypeCastingMixin,
)


class LogicalValue(
    AliasableMixin,
    ComparisonMixin,
    BooleanLogicMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """A boolean value expression used in SELECT lists.

    Renders TRUE/FALSE or boolean logic (AND/OR/NOT) as a **value** that can
    appear in a SELECT column list. Not a predicate — does not belong in
    WHERE/HAVING clauses.

    A predicate and this expression render the same SQL; what differs is what
    the caller may do with the result. Combining predicates stays a predicate
    -- that is how ``WHERE`` clauses are built -- while a truth value keeps
    its value type: ``(a & b)`` can be aliased into a ``SELECT`` list,
    compared, cast, and combined further. The class carries the same ``op``
    and ``operands`` shape
    :class:`~...predicates.LogicalPredicate` does, so both go through the one
    dialect entry point (``format_logical_predicate``).
    """

    def __init__(self, dialect: Any, op: str, *operands: Any):
        super().__init__(dialect)
        self.op = op
        # The names are the renderer's: the dialect formatter reads ``op`` and
        # ``operands`` whatever class carried them in, and the expression
        # contract stores every ``__init__`` parameter under its own name.
        self.operands = list(operands)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_logical_predicate"
