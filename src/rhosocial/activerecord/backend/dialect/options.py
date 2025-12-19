# src/rhosocial/activerecord/backend/dialect/options.py
"""Options and enumerations for SQL dialect functionality."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set




class ReturningType(Enum):
    """Type of RETURNING clause"""
    COLUMNS = "columns"
    EXPRESSIONS = "expressions"


@dataclass
class ReturningOptions:
    """
    Comprehensive configuration options for RETURNING clause.

    This class encapsulates all options related to RETURNING clause functionality
    across different database systems, supporting simple column lists, expressions,
    aliases, and database-specific features.
    """

    def __init__(self,
                 enabled: bool = False,
                 columns: Optional[List[str]] = None,
                 expressions: Optional[List[Dict[str, Any]]] = None,
                 aliases: Optional[Dict[str, str]] = None,
                 output_params: Optional[List[str]] = None,  # For Oracle/SQL Server output parameters
                 format: Optional[str] = None,  # Optional formatting style
                 force: bool = False,  # Force RETURNING even if compatibility issues exist
                 dialect_options: Optional[Dict[str, Any]] = None  # Database-specific options
                 ):
        """
        Initialize RETURNING options.

        Args:
            enabled: Whether RETURNING is enabled
            columns: List of column names to return
            expressions: List of expressions to return
            aliases: Dictionary mapping column/expression names to aliases
            output_params: List of output parameter names (for Oracle/SQL Server)
            format: Optional formatting style (database-specific)
            force: Force RETURNING even with known compatibility issues
            dialect_options: Database-specific options
        """
        self.enabled = enabled
        self.columns = columns or []
        self.expressions = expressions or []
        self.aliases = aliases or {}
        self.output_params = output_params or []
        self.format = format
        self.force = force
        self.dialect_options = dialect_options or {}

    @classmethod
    def from_legacy(cls, returning: bool, force: bool = False) -> 'ReturningOptions':
        """
        Create options from legacy boolean value.

        Args:
            returning: Legacy boolean returning flag
            force: Legacy force_returning flag

        Returns:
            ReturningOptions instance
        """
        return cls(enabled=returning, force=force)

    @classmethod
    def columns_only(cls, columns: List[str], force: bool = False) -> 'ReturningOptions':
        """
        Create options to return only specified columns.

        Args:
            columns: List of column names to return
            force: Force RETURNING even with known compatibility issues

        Returns:
            ReturningOptions instance
        """
        return cls(enabled=True, columns=columns, force=force)

    @classmethod
    def with_expressions(
                         cls,
                         expressions: List[Dict[str, Any]],
                         aliases: Optional[Dict[str, str]] = None,
                         force: bool = False) -> 'ReturningOptions':
        """
        Create options with expressions in RETURNING clause.

        Args:
            expressions: List of expressions to return
            aliases: Optional aliases for expressions
            force: Force RETURNING even with known compatibility issues

        Returns:
            ReturningOptions instance
        """
        return cls(enabled=True, expressions=expressions, aliases=aliases, force=force)

    @classmethod
    def all_columns(cls, force: bool = False) -> 'ReturningOptions':
        """
        Create options to return all columns.

        Args:
            force: Force RETURNING even with known compatibility issues

        Returns:
            ReturningOptions instance
        """
        return cls(enabled=True, force=force)

    def __bool__(self) -> bool:
        """
        Boolean conversion returns whether RETURNING is enabled.

        Returns:
            True if RETURNING is enabled, False otherwise
        """
        return self.enabled

    def has_column_specification(self) -> bool:
        """
        Check if specific columns or expressions are specified.

        Returns:
            True if specific columns or expressions are specified, False for RETURNING *
        """
        return bool(self.columns or self.expressions)