# src/rhosocial/activerecord/backend/expression/statements/ddl_partition.py
"""Table partitioning DDL expressions.

This module defines:

* the generic ``PartitionClause`` expression, which renders only the clause
  shape ``PARTITION BY <method> (<keys>)`` (the PostgreSQL form); and
* the structural ``PartitionDefinition`` / ``SubpartitionDefinition``
  declarations, which describe concrete partitions inline in CREATE TABLE.

Scope boundary
--------------
``PartitionClause`` intentionally carries **only the clause** (method + keys).
Named partitions, ``VALUES`` boundaries, storage options, and subpartitions are
backend-specific and live in backend expressions that derive from
``PartitionDefinition`` / ``SubpartitionDefinition`` (for example MySQL and
Oracle). Backends without declarative inline partitions (PostgreSQL creates
partitions through ``CREATE TABLE ... PARTITION OF``) never populate the
definition base classes.

``PartitionDefinition`` and ``SubpartitionDefinition`` are backend-agnostic
**structural declarations**, not renderable expressions: there is no portable
generic syntax for a partition boundary (``VALUES LESS THAN`` /
``VALUES IN`` / ``FOR VALUES`` all differ), so the owning dialect formatter
(``format_partition_definition``) renders them and backends override it.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Sequence, Type, TYPE_CHECKING, Union

from ..bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class PartitionStrategy(Enum):
    """Generic table partitioning strategies shared by supported backends."""

    RANGE = "RANGE"
    LIST = "LIST"
    HASH = "HASH"


@dataclass
class SubpartitionDefinition:
    """Base declaration for a single named subpartition.

    A backend-agnostic structural declaration. Backends add the boundary
    fields their syntax requires (Oracle's subpartition definitions carry
    ``less_than`` / ``in_values``; MySQL's carry only a name).

    Raises:
        ValueError: if ``name`` is empty or whitespace-only.
        TypeError: if ``dialect_options`` is not a dict when provided.
    """

    name: str
    dialect_options: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("subpartition name must be a non-empty string")
        if self.dialect_options is not None and not isinstance(self.dialect_options, dict):
            raise TypeError(
                "dialect_options must be dict or None, "
                f"got {type(self.dialect_options).__name__}"
            )


@dataclass
class PartitionDefinition:
    """Base declaration for an inline ``PARTITION ... VALUES ...`` definition.

    Holds the structural shape shared by backends that declare partitions
    inline in CREATE TABLE: a name plus an optional boundary (``less_than``
    for RANGE-like strategies or ``in_values`` for LIST-like strategies) and
    optional subpartition definitions.

    This is a backend-agnostic **structural declaration**, not a renderable
    expression; boundary SQL is produced by the backend's
    ``format_partition_definition``.

    Subclasses may tighten validation. MySQL additionally requires that at
    least one boundary form is present; Oracle permits neither (HASH).

    Raises:
        ValueError: if ``name`` is empty or whitespace-only, or if both
            ``less_than`` and ``in_values`` are provided.
        TypeError: if ``dialect_options`` is not a dict when provided.
    """

    name: str
    less_than: Optional[Sequence[BaseExpression]] = None
    in_values: Optional[Sequence[Union[BaseExpression, Sequence[BaseExpression]]]] = None
    subpartition_definitions: Optional[Sequence["SubpartitionDefinition"]] = None
    dialect_options: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("partition name must be a non-empty string")
        if self.less_than is not None and self.in_values is not None:
            raise ValueError("less_than and in_values are mutually exclusive")
        if self.dialect_options is not None and not isinstance(self.dialect_options, dict):
            raise TypeError(
                "dialect_options must be dict or None, "
                f"got {type(self.dialect_options).__name__}"
            )


class PartitionClause(BaseExpression):
    """Represents a generic PARTITION BY clause for DDL statements.

    The expression collects the minimal stable partition clause shape:
    ``PARTITION BY <method> (<keys>)``. It deliberately carries **only the
    clause**: concrete named partitions and their ``VALUES`` boundaries are
    described by :class:`PartitionDefinition` and rendered by backend
    formatters. Backend-specific partition clauses (for example MySQL's
    ``RANGE COLUMNS`` or Oracle's interval/reference partitioning) subclass
    this expression and add structured fields instead of placing core
    semantics into ``dialect_options``.

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

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_partition_clause"

