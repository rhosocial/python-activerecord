from abc import ABC, abstractmethod
from typing import Optional, Tuple

class SQLExpressionBase(ABC):
    """Base class for SQL expressions

    Used for embedding raw expressions in SQL, such as:
    - Arithmetic expressions: column + 1
    - Function calls: COALESCE(column, 0)
    - Subqueries: (SELECT MAX(id) FROM table)
    """

    def __init__(self, expression: str):
        self.expression = expression

    def __str__(self) -> str:
        return self.expression

    @classmethod
    def raw(cls, expression: str) -> 'SQLExpressionBase':
        """Create raw SQL expression"""
        return cls(expression)

    @abstractmethod
    def format(self, dialect: 'SQLDialectBase') -> str:
        """Format expression according to dialect

        Args:
            dialect: SQL dialect

        Returns:
            str: Formatted expression
        """
        pass

class SQLDialectBase(ABC):
    """Base class for SQL dialects

    Defines SQL syntax differences between database backends
    """

    @abstractmethod
    def format_expression(self, expr: SQLExpressionBase) -> str:
        """Format expression

        Args:
            expr: SQL expression

        Returns:
            str: Formatted expression
        """
        pass

    @abstractmethod
    def get_placeholder(self) -> str:
        """Get parameter placeholder

        Returns:
            str: Parameter placeholder (e.g., ? or %s)
        """
        pass

    @abstractmethod
    def create_expression(self, expression: str) -> SQLExpressionBase:
        """Create SQL expression"""
        pass

class SQLBuilder:
    """SQL Builder

    Used for building SQL statements containing expressions
    """

    def __init__(self, dialect: SQLDialectBase):
        self.dialect = dialect
        self.sql = ""
        self.params = []

    def build(self, sql: str, params: Optional[Tuple] = None) -> Tuple[str, Tuple]:
        """Build SQL and parameters

        Process expressions and parameter placeholders in SQL

        Args:
            sql: Raw SQL
            params: SQL parameters

        Returns:
            Tuple[str, Tuple]: (Processed SQL, Processed parameters)
        """
        if not params:
            return sql, ()

        # Find all placeholder positions
        placeholder = self.dialect.get_placeholder()
        placeholder_positions = []
        pos = 0
        while True:
            pos = sql.find(placeholder, pos)
            if pos == -1:
                break
            placeholder_positions.append(pos)
            pos += len(placeholder)

        if len(placeholder_positions) != len(params):
            raise ValueError(f"Parameter count mismatch: expected {len(placeholder_positions)}, got {len(params)}")

        # Record new positions for all parameters
        result = list(sql)
        final_params = []
        param_positions = []  # Record positions of parameters to keep

        # First pass: find all parameter positions to keep
        for i, param in enumerate(params):
            if not isinstance(param, SQLExpressionBase):
                param_positions.append(i)
                final_params.append(param)

        # Second pass: replace expressions from back to front
        for i in range(len(params) - 1, -1, -1):
            if isinstance(params[i], SQLExpressionBase):
                pos = placeholder_positions[i]
                expr_str = self.dialect.format_expression(params[i])
                result[pos:pos + len(placeholder)] = expr_str

        # Third pass: handle placeholders
        # To maintain the relative order of regular parameters,
        # we need to map the unsubstituted placeholders to the preserved parameters
        # according to their original relative order
        param_index = 0
        for i in range(len(params)):
            if i in param_positions:
                # This position is a regular parameter, keep the placeholder
                param_index += 1

        return ''.join(result), tuple(final_params)