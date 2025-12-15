# src/rhosocial/activerecord/backend/expression/literals.py
"""
Literal identifiers in SQL expressions.
"""
from typing import Tuple
from ..dialect import SQLDialectBase
from .base import SQLValueExpression


class Identifier(SQLValueExpression):
    """Represents a generic SQL identifier (e.g., table name, alias)."""
    def __init__(self, dialect: SQLDialectBase, name: str):
        """
        Initializes an Identifier SQL expression.

        Args:
            dialect: The SQL dialect instance to use for formatting this expression.
            name: The name of the identifier.
        """
        super().__init__(dialect)
        self.name = name

    def to_sql(self) -> Tuple[str, tuple]:
        # Delegate to dialect for identifier formatting/quoting
        return self.dialect.format_identifier(self.name), ()
    
    def __repr__(self) -> str: 
        return f"Identifier({self.name!r})"