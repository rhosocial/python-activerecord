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
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
)

from .bases import BaseExpression, SQLPredicate, SQLValueExpression
from .core import Column, Subquery

from .query_parts import OrderByClause

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


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


class CaseExpression(ArithmeticMixin, ComparisonMixin, SQLValueExpression):
    """Represents a CASE expression (e.g., CASE WHEN condition THEN result ELSE result END)."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        value: Optional["BaseExpression"] = None,
        cases: Optional[list] = None,
        else_result: Optional["BaseExpression"] = None,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
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
        elif hasattr(subquery, "to_sql"):
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


class WindowFunctionCall(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """
    Window function call, supporting inline window specification or named window reference
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        function_name: str,
        args: Optional[List[Union["BaseExpression", Any]]] = None,
        window_spec: Optional[Union[WindowSpecification, str]] = None,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.function_name = function_name
        self.args = args or []
        self.window_spec = window_spec
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_window_function_call"


class JSONDocumentExpression(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    TypeCastingMixin,
    JSONAccessorMixin,
    SQLValueExpression,
):
    """A JSON document reached by path -- ``->``.

    :meth:`~...expression.mixins.JSONAccessorMixin.json_value` returns one of
    these and ``.json_value("b")`` must work on it, so the accessor mixin is
    here as well as on :class:`~...expression.column_types.JSONColumn`.

    Not available: ``like`` / ``ilike`` and arithmetic. Those apply to the text
    a scalar path access returns, not to the document it navigated. Use
    :meth:`~...expression.mixins.JSONAccessorMixin.json_path` for the text
    form, which arrives as :class:`JSONTextExpression`.

    Split from that sibling rather than sharing one class: the two operations
    yield different types, and a single class could only offer the union of
    their operations to both.
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
        super().__init__(dialect)
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
    StringValueMixin,
    StringPatternPredicateMixin,
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
    and can be, which is why this class is the one without ``like``.
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
