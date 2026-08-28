# src/rhosocial/activerecord/backend/expression/statements/ddl_partition.py
"""Table partitioning DDL expressions.

This module defines the generic PARTITION BY clause expression used by
CREATE TABLE statements. The expression stores structured partition clause
parameters and delegates SQL generation to the dialect formatter.
"""

from enum import Enum
from typing import Any, Dict, Optional, Sequence, Type, TYPE_CHECKING

from ..bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class PartitionStrategy(Enum):
    """Generic table partitioning strategies shared by supported backends."""

    RANGE = "RANGE"
    LIST = "LIST"
    HASH = "HASH"


class PartitionClause(BaseExpression):
    """Represents a generic PARTITION BY clause for DDL statements.

    The expression collects the minimal stable partition clause shape:
    method name plus partition key expressions. Backend-specific partition
    forms should subclass this expression and add structured fields instead
    of placing core semantics into ``dialect_options``.

    SQL generation is always delegated to ``dialect.format_partition_clause``.
    """

    strategy_type: Type[Enum] = PartitionStrategy

    def __init__(
        self,
        dialect: "SQLDialectBase",
        method: Enum,
        keys: Sequence[BaseExpression],
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        if isinstance(method, self.strategy_type):
            normalized_method = method.value
        elif isinstance(method, str) and any(
            entry.value == method for entry in self.strategy_type
        ):
            # Accept the normalized string form produced by get_params() so
            # deserialization round-trips without needing the Enum object.
            normalized_method = method
        else:
            raise TypeError(
                f"method must be a {self.strategy_type.__name__} value or its "
                f"string value, got {type(method).__name__}"
            )
        if not isinstance(normalized_method, str):
            raise TypeError(f"{self.strategy_type.__name__} values must be strings")
        if not keys:
            raise ValueError("keys are required")
        for key in keys:
            if not isinstance(key, BaseExpression):
                raise TypeError(
                    "keys must contain BaseExpression instances, "
                    f"got {type(key).__name__}"
                )
        if dialect_options is not None and not isinstance(dialect_options, dict):
            raise TypeError(
                "dialect_options must be a dict when provided, "
                f"got {type(dialect_options).__name__}"
            )
        self.method = normalized_method
        self.keys = list(keys)
        self.dialect_options = dict(dialect_options or {})

    def to_sql(self) -> "SQLQueryAndParams":
        """Generate the PARTITION BY clause SQL via the dialect."""
        if not hasattr(self.dialect, "format_partition_clause"):
            from rhosocial.activerecord.backend.dialect import ProtocolNotImplementedError

            raise ProtocolNotImplementedError(
                dialect_name=self.dialect.name,
                protocol_name="PartitionSupport",
                required_by="PartitionClause",
            )
        return self.dialect.format_partition_clause(self)
