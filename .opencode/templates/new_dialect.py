# src/rhosocial/activerecord/backend/impl/{{backend_name}}/dialect.py
"""
{{BackendName}} SQL dialect implementation.
"""

from typing import Any, List, Optional, Tuple
from ...dialect import SQLDialectBase


class {{BackendName}}Dialect(SQLDialectBase):
    """
    {{backend_name}} SQL dialect.
    
    Implements {{backend_name}}-specific SQL generation.
    """
    
    def __init__(self):
        """Initialize dialect."""
        super().__init__()
        self.version = (1, 0, 0)  # Update with actual version detection
    
    # Identifier formatting
    def format_identifier(self, identifier: str) -> str:
        """
        Format identifier with proper quoting.
        
        Args:
            identifier: The identifier to quote
            
        Returns:
            Quoted identifier
        """
        return f'"{identifier}"'
    
    def format_string_literal(self, value: str) -> str:
        """
        Format string literal.
        
        Args:
            value: The string value
            
        Returns:
            SQL string literal
        """
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    
    def format_column_reference(
        self,
        table: Optional[str],
        column: str
    ) -> str:
        """
        Format column reference.
        
        Args:
            table: Table name (optional)
            column: Column name
            
        Returns:
            Formatted column reference
        """
        if table:
            return f'{self.format_identifier(table)}.{self.format_identifier(column)}'
        return self.format_identifier(column)
    
    # Feature support detection
    def supports_returning_clause(self) -> bool:
        """Check if RETURNING clause is supported."""
        return True
    
    def supports_window_functions(self) -> bool:
        """Check if window functions are supported."""
        return True
    
    def supports_cte(self) -> bool:
        """Check if CTE (Common Table Expressions) are supported."""
        return True
    
    def supports_recursive_cte(self) -> bool:
        """Check if recursive CTEs are supported."""
        return True
