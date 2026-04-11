# src/rhosocial/activerecord/backend/expression/statements/explain.py
"""EXPLAIN statement expressions."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

from ..bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


# region Explain Statement
class ExplainType(Enum):
    """EXPLAIN statement type, representing different analysis modes."""

    BASIC = "BASIC"  # Basic plan
    ANALYZE = "ANALYZE"  # Execute and analyze
    QUERY_PLAN = "QUERY_PLAN"  # Query plan
    PLAN = "PLAN"  # Execution plan
    FORMAT = "FORMAT"  # Formatted output
    PROFILE = "PROFILE"  # Performance profile


class ExplainFormat(Enum):
    """EXPLAIN output formats."""

    TEXT = "TEXT"  # Text format
    JSON = "JSON"  # JSON format
    XML = "XML"  # XML format
    YAML = "YAML"  # YAML format
    TREE = "TREE"  # Tree format
    TRADITIONAL = "TRADITIONAL"  # Traditional format


@dataclass
class ExplainOptions:
    """
    EXPLAIN options class to control the behavior of EXPLAIN statements.

    Note: Different databases support different sets of options, these options will be processed
    by the dialect implementation to generate suitable EXPLAIN statement for specific database.
    """

    # Options similar to PostgreSQL
    analyze: bool = False  # Execute query and show actual statistics
    verbose: bool = False  # Show additional plan information
    costs: bool = True  # Show plan cost estimates (enabled by default)
    buffers: bool = False  # Show buffer usage statistics
    timing: bool = False  # Show timing statistics for each node
    summary: bool = True  # Show summary information

    # Output format options
    format: Optional[ExplainFormat] = None  # Output format

    # Format-related options
    format_name: Optional[str] = None  # FORMAT=XXX format name
    analyze_format: Optional[bool] = None  # Format options for ANALYZE

    # General options
    type: Optional[ExplainType] = None  # Analysis type
    settings: bool = False  # Show settings impact (PostgreSQL)
    wal: bool = False  # Show WAL statistics

    # Dialect-specific options - for uncommon database options
    dialect_options: Optional[Dict[str, Any]] = None


class ExplainExpression(BaseExpression):
    """
    Unified EXPLAIN expression class that supports differences across database dialects.

    Due to the large differences in EXPLAIN syntax across different databases, this class
    collects options and delegates SQL generation to the specific dialect implementation.

    Usage Examples:
        # Basic EXPLAIN
        basic_explain = ExplainExpression(
            dialect,
            statement=query_stmt
        )

        # EXPLAIN with options
        detailed_explain = ExplainExpression(
            dialect,
            statement=query_stmt,
            options=ExplainOptions(
                analyze=True,          # Execute and analyze the query
                verbose=True,          # Show additional information
                costs=True,            # Include cost estimates
                buffers=True,          # Include buffer statistics
                format=ExplainFormat.JSON  # Output in JSON format
            )
        )

        # EXPLAIN with specific format
        formatted_explain = ExplainExpression(
            dialect,
            statement=query_stmt,
            options=ExplainOptions(
                format=ExplainFormat.TEXT,  # Text output format
                costs=True,                 # Include cost estimates
                buffers=False,              # Exclude buffer statistics
                timing=True                 # Include timing information
            )
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        statement: "BaseExpression",  # Statement to be analyzed
        options: Optional[ExplainOptions] = None,
    ):  # EXPLAIN options
        super().__init__(dialect)
        self.statement = statement  # SQL statement to analyze (query, insert, update, delete, etc.)
        self.options = options  # EXPLAIN options, keeping None if passed as None

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegate to dialect for EXPLAIN statement SQL generation."""
        return self.dialect.format_explain_statement(self)


# endregion Explain Statement
