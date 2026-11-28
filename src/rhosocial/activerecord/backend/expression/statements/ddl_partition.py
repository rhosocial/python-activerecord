# src/rhosocial/activerecord/backend/expression/statements/ddl_partition.py
"""Table partitioning DDL expressions (all expression nodes).

This module defines only ``BaseExpression`` derivatives:

* ``PartitionClause`` -- the generic ``PARTITION BY <word> (<keys>)`` clause,
  with dedicated strategy subclasses ``PartitionByRangeClause`` /
  ``PartitionByListClause`` / ``PartitionByHashClause`` (fixed ``.word``).
* ``PartitionDefinitionExpression`` / ``SubpartitionDefinitionExpression`` /
  ``PartitionOptionsExpression`` -- renderable nodes for inline partition
  boundaries, subpartitions and storage options.

There are no dataclasses or strategy enums here: a partition strategy is
expressed by the clause node's class/word, and a concrete partition definition
is a renderable expression. Both delegate SQL to the dialect via
``format_partition_clause`` / ``format_partition_definition`` (and the
subpartition/options formatters), which concrete backends override. Backends
without declarative inline partitions (e.g. PostgreSQL's ``CREATE TABLE ...
PARTITION OF``) simply do not use the definition nodes.
"""

from typing import Optional, Sequence, TYPE_CHECKING, Union

from ..bases.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase



class PartitionClause(BaseExpression):
    """Represents a generic PARTITION BY clause for DDL statements.

    The expression collects the minimal stable partition clause shape:
    ``PARTITION BY <method> (<keys>)``. It deliberately carries **only the
    clause**: concrete named partitions and their ``VALUES`` boundaries are
    described by :class:`PartitionDefinitionExpression` and rendered by backend
    formatters. Backend-specific partition clauses (for example MySQL's
    ``RANGE COLUMNS`` or Oracle's interval/reference partitioning) subclass
    this expression and add structured fields instead of placing core
    semantics into ``dialect_options``.

    SQL generation is always delegated to ``dialect.format_partition_clause``.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        method: str,
        keys: Sequence[BaseExpression],
    ):
        super().__init__(dialect)
        # The strategy is a plain word carried by the node (a non-empty string).
        # Dedicated clause subclasses (PartitionByRangeClause etc.) fix it via
        # their WORD; a word is what renders and what travels in an artifact.
        # Nothing is judged here: the constructor collects, and whether the
        # word and the key list can be rendered is answered by
        # :meth:`check_renderable` when SQL is asked for.
        self.method = method
        self.keys = list(keys)

    def check_renderable(self) -> None:
        """The clause needs a strategy word and at least one key expression."""
        if not isinstance(self.method, str) or not self.method.strip():
            raise TypeError(
                f"{type(self).__name__}.method must be a non-empty strategy word, "
                f"got {self.method!r}"
            )
        if not self.keys:
            raise TypeError(
                f"{type(self).__name__}.keys is empty: a PARTITION BY clause needs at least one key"
            )
        for key in self.keys:
            if not isinstance(key, BaseExpression):
                raise TypeError(
                    f"{type(self).__name__}.keys must contain BaseExpression instances, "
                    f"got {type(key).__name__}"
                )

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_partition_clause"


# --- Expression-only partition nodes (replace the strategy/definition dataclasses) ---
# These dedicated strategy clauses carry a fixed word (a plain str for artifact
# serialization) and reuse the dialect's `format_partition_clause` formatter.
# A strategy is now expressed by the node's class, not by a dataclass/enum.


class PartitionByRangeClause(PartitionClause):
    """``PARTITION BY RANGE (...)`` clause; strategy expressed by this node."""

    WORD = "RANGE"

    def __init__(self, dialect: "SQLDialectBase", keys: Sequence[BaseExpression]):
        super().__init__(dialect, self.WORD, keys)


class PartitionByListClause(PartitionClause):
    """``PARTITION BY LIST (...)`` clause."""

    WORD = "LIST"

    def __init__(self, dialect: "SQLDialectBase", keys: Sequence[BaseExpression]):
        super().__init__(dialect, self.WORD, keys)


class PartitionByHashClause(PartitionClause):
    """``PARTITION BY HASH (...)`` clause."""

    WORD = "HASH"

    def __init__(self, dialect: "SQLDialectBase", keys: Sequence[BaseExpression]):
        super().__init__(dialect, self.WORD, keys)


class PartitionDefinitionExpression(BaseExpression):
    """A single inline partition definition as a renderable expression.

    Holds the partition name,
    boundary expressions, optional storage options and subpartition expressions.
    Rendering is delegated to the dialect's ``format_partition_definition``
    formatter, which the inline-declaration backends already implement.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        *,
        less_than: Optional[Sequence[BaseExpression]] = None,
        in_values: Optional[Sequence[Union[BaseExpression, Sequence[BaseExpression]]]] = None,
        options: Optional["PartitionOptionsExpression"] = None,
        subpartitions: Optional[Sequence["SubpartitionDefinitionExpression"]] = None,
    ):
        super().__init__(dialect)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("partition name must be a non-empty string")
        if less_than is not None and in_values is not None:
            raise ValueError("less_than and in_values are mutually exclusive")
        self.name = name
        self.less_than = less_than
        self.in_values = in_values
        self.options = options
        self.subpartitions = subpartitions

    @property
    def format_method(self) -> str:
        return "format_partition_definition_expression"


class SubpartitionDefinitionExpression(BaseExpression):
    """A single named subpartition definition as a renderable expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        *,
        less_than: Optional[Sequence[BaseExpression]] = None,
        in_values: Optional[Sequence[BaseExpression]] = None,
    ):
        super().__init__(dialect)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("subpartition name must be a non-empty string")
        self.name = name
        self.less_than = less_than
        self.in_values = in_values

    @property
    def format_method(self) -> str:
        return "format_subpartition_definition_expression"


class PartitionOptionsExpression(BaseExpression):
    """Storage options for a partition definition, as a renderable expression.

    Holds backend-specific option expressions; the owning dialect formatter
    renders them via ``format_partition_definition_options``.
    """

    def __init__(self, dialect: "SQLDialectBase", options: Optional[dict] = None):
        super().__init__(dialect)
        self.options = dict(options or {})

    @property
    def format_method(self) -> str:
        return "format_partition_options_expression"
