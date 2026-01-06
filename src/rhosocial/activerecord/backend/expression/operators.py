# src/rhosocial/activerecord/backend/expression/operators.py
"""
SQL operations like binary, unary, and arithmetic expressions.
"""
from typing import Any, Tuple, List, TYPE_CHECKING
from . import bases
from . import mixins

if TYPE_CHECKING: # pragma: no cover
    from ..dialect import SQLDialectBase


class SQLOperation(bases.BaseExpression):
    """Represents a generic SQL operation."""
    def __init__(self, dialect: "SQLDialectBase", op: str, *operands: "bases.BaseExpression"):
        super().__init__(dialect)
        self.op = op
        self.operands = list(operands)

    def to_sql(self) -> Tuple[str, tuple]:
        formatted_operands_sql = []
        params: List[Any] = []
        for operand in self.operands:
            operand_sql, operand_params = operand.to_sql()
            formatted_operands_sql.append(operand_sql)
            params.extend(operand_params)
        if self.operands:
            return f"{self.op}({', '.join(formatted_operands_sql)})", tuple(params)
        else:
            return f"{self.op}()", tuple(params)


class BinaryExpression(bases.BaseExpression):
    """Represents a binary SQL operation."""
    def __init__(self, dialect: "SQLDialectBase", op: str, left: "bases.BaseExpression", right: "bases.BaseExpression"):
        super().__init__(dialect)
        self.op = op
        self.left = left
        self.right = right

    def to_sql(self) -> Tuple[str, tuple]:
        left_sql, left_params = self.left.to_sql()
        right_sql, right_params = self.right.to_sql()
        return self.dialect.format_binary_operator(self.op, left_sql, right_sql, left_params, right_params)


class UnaryExpression(bases.BaseExpression):
    """Represents a unary SQL operation."""
    def __init__(self, dialect: "SQLDialectBase", op: str, operand: "bases.BaseExpression", pos: str = 'before'):
        super().__init__(dialect)
        self.op = op
        self.operand = operand
        self.pos = pos

    def to_sql(self) -> Tuple[str, tuple]:
        operand_sql, operand_params = self.operand.to_sql()
        return self.dialect.format_unary_operator(self.op, operand_sql, self.pos, operand_params)


class RawSQLExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    """Represents a raw SQL expression string that is directly embedded."""
    def __init__(self, dialect: "SQLDialectBase", expression: str, params: tuple = ()):
        super().__init__(dialect)
        self.expression = expression
        self.params = params

    def to_sql(self) -> Tuple[str, tuple]:
        return self.expression, self.params


class BinaryArithmeticExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """Represents a binary arithmetic operation."""
    def __init__(self, dialect: "SQLDialectBase", op: str, left: "bases.SQLValueExpression", right: "bases.SQLValueExpression"):
        super().__init__(dialect)
        self.op = op
        self.left = left
        self.right = right

    def to_sql(self) -> Tuple[str, tuple]:
        left_sql, left_params = self.left.to_sql()
        right_sql, right_params = self.right.to_sql()

        # Get the precedence of the current operator
        current_precedence = self.OPERATOR_PRECEDENCE.get(self.op, 0)

        # Check if left operand needs parentheses based on precedence
        left_needs_parens = self._needs_parens(self.left, current_precedence)
        if left_needs_parens:
            left_sql = f"({left_sql})"

        # Check if right operand needs parentheses based on precedence
        right_needs_parens = self._needs_parens(self.right, current_precedence)
        if right_needs_parens:
            right_sql = f"({right_sql})"

        return self.dialect.format_binary_arithmetic_expression(self.op, left_sql, right_sql, left_params, right_params)

    def _needs_parens(self, operand, current_precedence):
        """Check if an operand needs parentheses based on precedence."""
        # If operand is another BinaryArithmeticExpression, check its precedence
        if isinstance(operand, BinaryArithmeticExpression):
            operand_precedence = self.OPERATOR_PRECEDENCE.get(operand.op, 0)
            # If operand has lower precedence, it needs parentheses when used in higher precedence context
            return operand_precedence < current_precedence
        # For other expressions (like FunctionCall, Column, Literal),
        # they have the highest precedence and don't need parentheses
        return False

    # Define operator precedence levels for arithmetic operations (lower number means lower precedence)
    OPERATOR_PRECEDENCE = {
        '+': 9, '-': 9,  # Addition and subtraction
        '*': 10, '/': 10, '%': 10,  # Multiplication, division, modulo
    }
