# src/rhosocial/activerecord/backend/expression/operators.py
"""
SQL operations like binary, unary, and arithmetic expressions.
"""
from typing import Any, Tuple, Union, Optional, List, TYPE_CHECKING
from ..dialect import SQLDialectBase

if TYPE_CHECKING:
    from .base import SQLValueExpression, SQLPredicate, BaseExpression


class SQLOperation:
    """
    Represents a generic SQL operation.
    In this new design, specific operation types (Unary, Binary, etc.)
    will handle their own formatting. This class remains as a fallback
    or for highly generic operations that don't fit specific categories.
    """
    def __init__(self,
                 dialect: SQLDialectBase,
                 op: str,
                 *operands: "BaseExpression"):
        """
        Initializes a generic SQL operation expression.

        Args:
            dialect: The SQL dialect instance to use for formatting this operation.
            op: The operator or function name (e.g., "AND", "SUM", "COALESCE").
            *operands: Positional arguments representing the operands of the operation.
                       Each operand must be an instance of SQLExpression.
        """
        self._dialect = dialect
        self.op = op
        self.operands = list(operands)
    
    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def to_sql(self) -> Tuple[str, tuple]:
        # This will be overridden or delegated more specifically
        # For now, it will use a generic n-ary formatting
        formatted_operands_sql = []
        params: List[Any] = []
        for operand in self.operands:
            operand_sql, operand_params = operand.to_sql()
            formatted_operands_sql.append(operand_sql)
            params.extend(operand_params)
        
        # Delegate to a generic n-ary operator formatter in dialect
        # This might be further refined to be a method like format_function_call
        # or format_n_ary_operator based on the `op`
        if self.operands:
            return f"{self.op}({', '.join(formatted_operands_sql)})", tuple(params)
        else: # Zero-ary, e.g., NOW()
            return f"{self.op}()", tuple(params)


class BinaryExpression:
    """Represents a binary SQL operation (e.g., expr1 = expr2, expr1 + expr2)."""
    def __init__(self, dialect: SQLDialectBase, op: str, left: "BaseExpression", right: "BaseExpression"):
        """
        Initializes a binary SQL expression.

        Args:
            dialect: The SQL dialect instance to use for formatting this expression.
            op: The binary operator (e.g., "=", "+", "AND", "LIKE").
            left: The left-hand side operand (SQLExpression).
            right: The right-hand side operand (SQLExpression).
        """
        self._dialect = dialect
        self.op = op
        self.left = left
        self.right = right
    
    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def to_sql(self) -> Tuple[str, tuple]:
        left_sql, left_params = self.left.to_sql()
        right_sql, right_params = self.right.to_sql()

        return self.dialect.format_binary_operator(self.op, left_sql, right_sql, left_params, right_params)


class UnaryExpression:
    """Represents a unary SQL operation (e.g., NOT expr, expr IS NULL)."""
    def __init__(self, dialect: SQLDialectBase, op: str, operand: "BaseExpression", pos: str = 'before'):
        """
        Initializes a unary SQL expression.

        Args:
            dialect: The SQL dialect instance to use for formatting this expression.
            op: The unary operator (e.g., "NOT", "IS NULL").
            operand: The operand of the unary operation (SQLExpression).
            pos: The position of the operator relative to the operand ('before' or 'after').
        """
        self._dialect = dialect
        self.op = op
        self.operand = operand
        self.pos = pos # 'before' or 'after'
    
    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def to_sql(self) -> Tuple[str, tuple]:
        operand_sql, operand_params = self.operand.to_sql()

        return self.dialect.format_unary_operator(self.op, operand_sql, self.pos, operand_params)


class RawSQLExpression:
    """Represents a raw SQL expression string that is directly embedded."""
    def __init__(self, dialect: SQLDialectBase, expression: str):
        """
        Initializes a raw SQL expression.

        Args:
            dialect: The SQL dialect instance to use for formatting this expression.
            expression: The raw SQL string to embed.
        """
        self._dialect = dialect
        self.expression = expression
    
    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def to_sql(self) -> Tuple[str, tuple]:
        return self.expression, () # Raw expression has no parameters


class BinaryArithmeticExpression:
    """Represents a binary arithmetic operation (e.g., expr1 + expr2, expr1 * expr2)."""
    def __init__(self, dialect: SQLDialectBase, op: str, left: "SQLValueExpression", right: "SQLValueExpression"):
        """
        Initializes a binary arithmetic expression.

        Args:
            dialect: The SQL dialect instance.
            op: The arithmetic operator (e.g., "+", "-", "*", "/").
            left: The left-hand side expression.
            right: The right-hand side expression.
        """
        self._dialect = dialect
        self.op = op
        self.left = left
        self.right = right
    
    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def to_sql(self) -> Tuple[str, tuple]:
        left_sql, left_params = self.left.to_sql()
        right_sql, right_params = self.right.to_sql()

        return self.dialect.format_binary_arithmetic_expression(self.op, left_sql, right_sql, left_params, right_params)
