# src/rhosocial/activerecord/backend/expression/statements/ddl_partition.py
"""Table partitioning DDL expressions and related types.

This module defines expressions for table partitioning, including the
PARTITION BY clause in CREATE TABLE statements and partitioning type definitions.

Architecture:
- PartitionStrategy, PartitionKey: Data types for partition specification
- PartitionClause: Expression for PARTITION BY clause, delegates to dialect.format_partition_clause()
- Dialects implement PartitionSupport protocol with format_partition_clause() method
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from ..bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class PartitionStrategy(Enum):
    """Standard table partitioning strategies."""

    RANGE = "RANGE"
    LIST = "LIST"
    HASH = "HASH"


@dataclass
class PartitionKey:
    """Represents the key used to route rows into table partitions.

    Attributes:
        columns: List of column names for the partition key.
        expression: Optional expression for expression-based partitioning.
            Mutually exclusive with columns.
        dialect_options: Database-specific options (e.g., MySQL KEY partitioning).
    """

    columns: List[str] = field(default_factory=list)
    expression: Optional["BaseExpression"] = None
    dialect_options: Optional[Dict[str, Any]] = None


class PartitionClause(BaseExpression):
    """Represents a PARTITION BY clause for CREATE TABLE statements.

    This expression generates the PARTITION BY clause of a CREATE TABLE
    statement, delegating SQL generation to the dialect's
    format_partition_clause() method.

    The dialect is responsible for:
    - Validating the partition strategy
    - Formatting the partition key (columns or expression)
    - Applying any dialect-specific syntax

    Attributes:
        strategy: Partitioning strategy (RANGE, LIST, HASH) or a string
            for dialect-specific strategies.
        key: The partition key definition.
        dialect_options: Database-specific partitioning options.

    Example:
        >>> from rhosocial.activerecord.backend.expression import PartitionClause, PartitionStrategy, PartitionKey
        >>> from rhosocial.activerecord.backend.impl.dummy import DummyDialect
        >>> dialect = DummyDialect()
        >>> key = PartitionKey(columns=["created_at"])
        >>> partition = PartitionClause(
        ...     dialect=dialect,
        ...     strategy=PartitionStrategy.RANGE,
        ...     key=key,
        ... )
        >>> sql, params = partition.to_sql()
        >>> sql
        ' PARTITION BY RANGE (created_at)'
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        strategy: Union[PartitionStrategy, str],
        key: PartitionKey,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.strategy = strategy
        self.key = key
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        """Generate the PARTITION BY clause SQL.

        Delegates to the dialect's format_partition_clause() method.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return self.dialect.format_partition_clause(self)
