# src/rhosocial/activerecord/backend/expression/advanced_functions.py
"""
Advanced SQL functions and expressions like CASE, EXISTS, ANY/ALL, Window functions,
JSON operations, and Array operations.
"""
from enum import Enum
from typing import Any, List, Optional, Union, TYPE_CHECKING

from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    JSONAccessorMixin,
    StringValueMixin,
    TypeCastingMixin,
)

from .bases import BaseExpression, SQLPredicate, SQLValueExpression
from .core import (
    Column,
    JSONValueExpression,
    StringValueExpression,
    Subquery,
)

from .query_parts import OrderByClause

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class DeclaredValueType:
    """Render this node itself rather than the call a value class would wrap.

    The typed value classes in :mod:`..core` are *wrappers*: they hold a node
    and delegate ``to_sql`` to it, which is what lets one class stand for
    ``length(x)``, ``min(name)`` and ``CURRENT_USER`` alike. The nodes here are
    not wrappers -- ``EXTRACT``, ``col->'$.a'`` and ``CASE`` each have their own
    formatter and their own fields -- so when such a node class declares the
    value type it *is*, it needs the base implementation back rather than the
    wrapper's delegation to a node it does not hold.

    Inheriting the value class is what makes the result readable off the
    object: ``isinstance(expr, TimestampValueExpression)`` holds because the
    class says so, not because a tag was attached after construction.
    """

    def to_sql(self):
        """Render through this node's own ``format_method``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return BaseExpression.to_sql(self)


class JSONPathMode(Enum):
    """How a JSON path expression should be rendered by the dialect.

    - ``AUTO``: Use arrow operators if supported, else function-based.
    - ``ARROW``: Force arrow operators (-> / ->>); raises if unsupported.
    - ``FUNCTION``: Force function-based formatting (e.g. JSON_EXTRACT).
    """
    AUTO = "auto"
    ARROW = "arrow"
    FUNCTION = "function"

    @classmethod
    def from_value(cls, value) -> "JSONPathMode":
        """Coerce None / str / JSONPathMode to a valid JSONPathMode."""
        if value is None:
            return cls.AUTO
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(value)
        raise TypeError(f"mode must be None, str, or JSONPathMode; got {type(value).__name__}")


#: Value class -> the class standing for both a CASE and that value class.
#: Populated on first use by :meth:`CaseExpression._class_for`; see there for
#: why it is built at all and why it is kept.
_CASE_VALUE_CLASSES = {}


class CaseExpression(
    DeclaredValueType,
    ArithmeticMixin,
    ComparisonMixin,
    SQLValueExpression,
):
    """Represents a CASE expression (e.g., CASE WHEN condition THEN result ELSE result END).

    A CASE answers with whatever its branches answer with, so the branches
    decide it -- not the factory, which is handed the whole list rather than the
    individual results. What each branch is is read off its own class, so
    :func:`~...expression.column_types.value_class_of` is the question asked of
    each one.

    **Agreement is over the branches, and a branch that says nothing is not a
    contradiction.** ``CASE WHEN i THEN literal ELSE i`` is still an integer:
    a ``Literal`` declares no kind, so it neither agrees nor disagrees, and what
    matters is that the branches which *do* declare a kind declare the same one.

    When they agree, the node is built as an instance of the agreed value class
    so the answer is readable off the object. When they disagree -- integer here
    and float there -- the CASE is legal SQL that answers with neither kind, so
    no typed wrapper is offered and the bare class stands for it. Guessing the
    first branch or the widest would promise a surface the database does not
    have, and "unknown" is a result the caller can handle.

    That is why this class declares no single value type of its own: the answer
    is per-instance, and :class:`DeclaredValueType` keeps it rendering itself
    whichever it turns out to be.
    """

    def __new__(cls, dialect=None, value=None, cases=None, else_result=None, alias=None):
        """Build as the agreed value class, when the branches declare one.

        Returns an instance of a class that *is* both this CASE and the agreed
        value class, or of ``cls`` alone when the branches disagree or none of
        them declares a kind. :meth:`__init__` then runs against whichever came
        back, so the state is set the same way either way.

        ``dialect`` is optional and the branches are optional because
        ``copy.copy`` reconstructs through this: ``as_()`` returns a copy, and
        that copy must not re-run the consensus check on branches it already
        agreed about. Reconstruction passes no branches, so the copy keeps the
        class it was made from -- which is the correct answer anyway, since
        nothing about it changed.
        """
        if cases is None and else_result is None and value is None:
            return super().__new__(cls)

        from .column_types import value_class_of

        branches = [result for _condition, result in cases] + [else_result]
        declared = {value_class_of(branch) for branch in branches} - {None}
        if len(declared) != 1:
            return super().__new__(cls)
        agreed = declared.pop()
        combined = cls._class_for(agreed)
        # object.__new__, not combined.__new__: `combined` inherits this very
        # __new__, which would recurse back through the consensus check.
        return object.__new__(combined)

    @classmethod
    def _class_for(cls, value_class):
        """The class standing for both this CASE and *value_class*.

        Built once per value class and kept, because building it per expression
        would make ``type(x)`` differ between two CASE expressions that answer
        with the same thing -- which is the thing being fixed.

        The bases are ordered so that ``CaseExpression`` supplies the CASE
        state and ``format_method``, :class:`DeclaredValueType` supplies the
        rendering, and *value_class* supplies the operations and the value type.
        The value class's own ``to_sql`` is deliberately *not* reached: it is a
        wrapper delegating to a node this does not hold.
        """
        try:
            return _CASE_VALUE_CLASSES[value_class]
        except KeyError:
            combined = type(
                f"Case{value_class.__name__}",
                (cls, DeclaredValueType, value_class),
                {
                    "__doc__": (
                        f"A CASE whose branches agree the answer is a "
                        f"{value_class.__name__}, so it is one."
                    )
                },
            )
            _CASE_VALUE_CLASSES[value_class] = combined
            return combined

    def __init__(
        self,
        dialect: "SQLDialectBase",
        value: Optional["BaseExpression"] = None,
        cases: Optional[list] = None,
        else_result: Optional["BaseExpression"] = None,
        alias: Optional[str] = None,
    ):
        # BaseExpression rather than super(): the agreed value class, when there
        # is one, is a wrapper and would want a node to hold -- this is the node.
        BaseExpression.__init__(self, dialect)
        self.value = value
        self.cases = cases or []
        self.else_result = else_result
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_case_expression"


class ExistsExpression(SQLPredicate):
    """Represents an EXISTS predicate (e.g., EXISTS(subquery))."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_exists_expression"

    def __init__(self, dialect: "SQLDialectBase", subquery: Union["Subquery", "BaseExpression"], is_not: bool = False):
        super().__init__(dialect)
        # Automatically wrap BaseExpression in Subquery if needed
        if isinstance(subquery, Subquery):
            self.subquery = subquery
        elif isinstance(subquery, BaseExpression):
            # Create a Subquery from BaseExpression
            self.subquery = Subquery(dialect, subquery)
        else:
            raise TypeError(f"subquery must be Subquery or BaseExpression, got {type(subquery)}")
        self.is_not = is_not


class AnyExpression(SQLPredicate):
    """Represents an ANY predicate (e.g., expr = ANY(array_expr) or expr > ANY(subquery))."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_any_expression"

    def __init__(self, dialect: "SQLDialectBase", expr: "BaseExpression", op: str, array_expr: "BaseExpression"):
        super().__init__(dialect)
        self.expr = expr
        self.op = op
        self.array_expr = array_expr


class AllExpression(SQLPredicate):
    """Represents an ALL predicate (e.g., expr > ALL(array_expr) or expr = ALL(subquery))."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_all_expression"

    def __init__(self, dialect: "SQLDialectBase", expr: "BaseExpression", op: str, array_expr: "BaseExpression"):
        super().__init__(dialect)
        self.expr = expr
        self.op = op
        self.array_expr = array_expr


class WindowFrameSpecification(BaseExpression):
    """Window frame specification (frame_type [BETWEEN start_frame AND end_frame])"""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        frame_type: str,  # 'ROWS', 'RANGE', 'GROUPS'
        start_frame: str,  # 'UNBOUNDED PRECEDING', 'N PRECEDING', 'CURRENT ROW', etc.
        end_frame: Optional[str] = None,  # 'UNBOUNDED FOLLOWING', 'N FOLLOWING', etc.
    ):
        super().__init__(dialect)
        self.frame_type = frame_type
        self.start_frame = start_frame
        self.end_frame = end_frame

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_window_frame_specification"


class WindowSpecification(BaseExpression):
    """Window specification (PARTITION BY ..., ORDER BY ..., frame)"""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        partition_by: Optional[List[Union["BaseExpression", str]]] = None,
        order_by: Optional[Union["OrderByClause", str]] = None,  # Accept only single OrderByClause or str
        frame: Optional[WindowFrameSpecification] = None,
    ):
        super().__init__(dialect)
        self.partition_by = partition_by or []

        # Strictly validate and process order_by parameter
        if order_by is None:
            self.order_by = None
        elif isinstance(order_by, str):
            # Convert string to OrderByClause - create a column expression from the string
            self.order_by = OrderByClause(dialect, [Column(dialect, order_by)])
        elif isinstance(order_by, OrderByClause):
            self.order_by = order_by
        else:
            raise TypeError(f"order_by must be OrderByClause or str, got {type(order_by)}")

        self.frame = frame

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_window_specification"


class WindowDefinition(BaseExpression):
    """Named window definition (name AS window_specification)"""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        specification: WindowSpecification,
    ):
        super().__init__(dialect)
        self.name = name
        self.specification = specification

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_window_definition"


class WindowClause(BaseExpression):
    """Complete WINDOW clause"""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        definitions: List[WindowDefinition],
    ):
        super().__init__(dialect)
        self.definitions = definitions

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_window_clause"


class JSONDocumentExpression(
    DeclaredValueType,
    JSONValueExpression,
    ArithmeticMixin,
    JSONAccessorMixin,
    SQLValueExpression,
):
    """A JSON document reached by path -- ``->``.

    :meth:`~...expression.mixins.JSONAccessorMixin.json_value` returns one of
    these and ``.json_value("b")`` must work on it, so the accessor mixin is
    here as well as on :class:`~...expression.column_types.JSONColumn`.

    Not available: ``like`` / ``ilike``. Those apply to the text a scalar path
    access returns, not to the document it navigated. Use
    :meth:`~...expression.mixins.JSONAccessorMixin.json_path` for the text
    form, which arrives as :class:`JSONTextExpression`.

    Split from that sibling rather than sharing one class: the two operations
    yield different types, and a single class could only offer the union of
    their operations to both.

    It is a :class:`~...expression.core.JSONValueExpression` because that is what
    a document is. It is not a *wrapper* holding one -- it has its own formatter
    and its own fields -- so it says so with
    :class:`DeclaredValueType` rather than inheriting the delegation.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        column: Union["BaseExpression", str],
        path: str,
        operation: str = "->",
        alias: Optional[str] = None,
        mode: Union[None, str, "JSONPathMode"] = None,
    ):
        # BaseExpression rather than super(): the value class this inherits is a
        # wrapper and wants a node to hold, and this class is the node.
        BaseExpression.__init__(self, dialect)
        self.column = column
        self.path = path
        self.operation = operation
        self.alias = alias
        self.mode = JSONPathMode.from_value(mode)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_expression"


class JSONTextExpression(
    JSONDocumentExpression,
    StringValueExpression,
):
    """A JSON path access that yielded **text** -- ``->>``.

    The sibling of :class:`JSONDocumentExpression`, and the reason that one is
    split from this: ``->`` hands back a document and ``->>`` hands back a
    scalar, and they are different types with different operations. It used to
    be one class whose ``operation`` decided the answer at construction, which
    meant the operations on offer could not be read off the class -- a JSON
    document would offer ``like``, because the one class could be either.

    Text is the narrower of the two, so chaining continues: ``->>`` yields a
    scalar and a scalar cannot be navigated further. ``->`` yields a document
    and can be, which is why this is the class that gains
    :class:`~...expression.core.StringValueExpression` and its operations.

    One consequence of inheriting the document class is that the JSON accessors
    stay reachable here too: ``DeclaredValueType`` renders the node and this
    class does not hold one, so it cannot drop the mixin without also losing
    ``json_value``. That is a known over-offer -- a scalar is not navigable --
    and it is stated in the test that covers it rather than papered over.
    """


class ArrayExpression(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Represents array operations like ANY, ALL, and array access."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        operation: str,
        base_expr: Optional["BaseExpression"] = None,
        index_expr: Optional["BaseExpression"] = None,
        elements: Optional[List["BaseExpression"]] = None,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.operation = operation
        self.base_expr = base_expr
        self.index_expr = index_expr
        self.elements = elements
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_array_expression"


class OrderedSetAggregation(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Represents an ordered-set aggregate function call with WITHIN GROUP (ORDER BY ...)."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        func_name: str,
        args: List["BaseExpression"],
        order_by: Union["OrderByClause", str],
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.func_name = func_name
        self.args = args

        # Strictly validate and process order_by parameter - accept OrderByClause or str
        if isinstance(order_by, str):
            self.order_by = OrderByClause(dialect, [Column(dialect, order_by)])
        elif isinstance(order_by, OrderByClause):
            self.order_by = order_by
        else:
            raise TypeError(f"order_by must be OrderByClause or str, got {type(order_by)}")

        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_ordered_set_aggregation"
