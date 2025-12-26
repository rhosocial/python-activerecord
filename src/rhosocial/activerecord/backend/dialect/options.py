"""
SQL dialect options for rhosocial-activerecord.

This module defines dataclasses for encapsulating various SQL dialect options
that control query generation and execution behavior.
"""
from dataclasses import dataclass
from typing import List, Optional, Union


@dataclass
class ReturningOptions:
    """
    Encapsulates options for RETURNING clause generation.

    This class defines the parameters that control how RETURNING clauses
    are generated and processed by SQL dialects.
    """
    # List of column names to return
    columns: Optional[List[str]] = None

    # Whether to return all columns
    all_columns: bool = False

    # Additional options for specific dialects
    dialect_options: Optional[dict] = None

    @classmethod
    def from_columns(cls, columns: Union[List[str], bool]) -> 'ReturningOptions':
        """
        Create ReturningOptions from a list of columns or boolean.

        Args:
            columns: List of column names or boolean indicating all columns

        Returns:
            ReturningOptions instance
        """
        if isinstance(columns, bool):
            return cls(all_columns=columns)
        return cls(columns=columns)


@dataclass
class ExplainOptions:
    """
    Encapsulates options for EXPLAIN statement generation.

    This class defines the parameters that control how EXPLAIN statements
    are generated and processed by SQL dialects.
    """
    # Whether to analyze the query execution
    analyze: bool = False

    # Format for the explain output (TEXT, JSON, XML, YAML)
    format: Optional[str] = None

    # Whether to include costs in the output
    costs: bool = True

    # Whether to include buffers information
    buffers: bool = False

    # Whether to include timing information
    timing: bool = False

    # Whether to include verbose output
    verbose: bool = False

    # Additional settings for PostgreSQL-specific options
    settings: bool = False

    # WAL statistics for PostgreSQL
    wal: bool = False


@dataclass
class ExplainType:
    """
    Enum-like class for EXPLAIN statement types.
    """
    EXPLAIN = "EXPLAIN"
    ANALYZE = "ANALYZE"


@dataclass
class ExplainFormat:
    """
    Enum-like class for EXPLAIN format options.
    """
    TEXT = "TEXT"
    JSON = "JSON"
    XML = "XML"
    YAML = "YAML"


@dataclass
class ViewOptions:
    """
    Encapsulates options for VIEW statement generation.
    """
    # Whether to replace the view if it exists
    replace: bool = False

    # Whether the view is temporary
    temporary: bool = False

    # Check option for the view
    check_option: Optional[str] = None


@dataclass
class ViewCheckOption:
    """
    Enum-like class for VIEW CHECK OPTION values.
    """
    NONE = None
    LOCAL = "LOCAL"
    CASCADED = "CASCADED"