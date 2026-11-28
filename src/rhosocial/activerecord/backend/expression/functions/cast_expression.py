# src/rhosocial/activerecord/backend/expression/functions/cast_expression.py
from typing import Optional, TYPE_CHECKING

from ..bases.bases import SQLValue
from ..bases.mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from ..types._base import DataType


class CastExpression(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
    SQLValue,
):
    """Represents a SQL type cast as a proper AST node.

    The ``Expression`` suffix is not a fallback spelling: it transcribes the
    standard production this node stands for -- ISO/IEC 9075-2
    ``<cast specification>``. Per spec §4.9 (the "scalar expression special
    forms" row) a CAST is a scalar-expression production rather than a routine
    invocation, so it is neither a ``*Function`` nor a ``*Clause``; the name is
    kept verbatim from the standard and the ``*Expression`` suffix is the
    retired spelling's single exemption class.

    ``CAST(expression AS target_type)`` is a **unary tree node**: its single
    child is the wrapped expression and ``target_type`` is a construction
    parameter. The constructor only collects that parameter; the type-position
    check lives in the public :meth:`validate_target_type`, which a formatter
    may call before rendering. Rendering is delegated to the dialect's
    ``format_cast_expression``.

    Chained ``cast()`` calls therefore nest like any other expression —
    ``expr.cast(A).cast(B)`` renders ``CAST(CAST(expr AS A) AS B)``.
    When the wrapped expression carries an alias, ``cast()`` hoists the
    alias onto the new node (the alias decorates the outermost rendered
    form), so ``col.cast(IntegerType(dialect)).as_("v")`` and
    ``col.as_("v").cast(IntegerType(dialect))`` both render
    ``CAST(col AS INTEGER) AS v``.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_cast_expression"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expression: "SQLValue",
        target_type: "DataType",
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.expression = expression
        self.target_type = target_type
        self.alias = alias

    def validate_target_type(self) -> None:
        """Refuse a target that is not a :class:`DataType` node.

        The type position of ``CAST(expr AS type)`` is a grammar production,
        not an expression, so no bound parameter can be used there and a
        free-form string would be rendered straight into the statement.
        Requiring a ``DataType`` makes that impossible by validation rather
        than by accepting a string that someone else could widen later.

        This is a public, opt-in check: the constructor only collects
        ``target_type`` and each formatter decides whether to call it before
        spelling the type. The message is unchanged from when the check ran in
        ``__init__``, so callers refuse a bad target with the same ``TypeError``.
        """
        from ..types._base import DataType as _DataType

        if not isinstance(self.target_type, _DataType):
            raise TypeError(
                f"cast() takes a DataType instance, not "
                f"{type(self.target_type).__name__}. Use IntegerType(dialect) rather "
                f"than a string: the type position cannot be bound, so a string "
                f"is rendered into the SQL. A user-defined type is a DataType "
                f"subclass, registered so dialects can render it."
            )

    def __repr__(self) -> str:
        return f"CastExpression({self.expression!r} AS {self.target_type!r})"
