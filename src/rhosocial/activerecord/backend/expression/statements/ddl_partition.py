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
from typing import Optional, Sequence, Type, TYPE_CHECKING, Union

from ..bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class PartitionStrategy(str, Enum):
    """Generic table partitioning strategies shared by supported backends.

    ``str`` because a strategy is a JSON scalar in the artifact, not a node:
    changing it changes the rendered SQL and nothing else (§4), so it travels as
    the word it is. Without the ``str`` base it would be the one closed value
    set in the expression layer that no artifact could carry (§11.3).

    A dialect that supports only some of these gates the rest in
    ``format_partition_clause``, raising rather than rendering a word its
    database will reject — an unsupported strategy is an explicit refusal, not a
    silent omission (§6).
    """

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    RANGE = "RANGE"
    LIST = "LIST"
    HASH = "HASH"

    @classmethod
    def parse(cls, method: Union["PartitionStrategy", str]) -> str:
        """The wire word for *method*, from the member or from its spelling.

        Normalisation lives here rather than in the caller, so
        ``PartitionClause`` says what it takes and this says what that looks
        like. The entry stays wide — the member and the string both land on the
        same word, which is what lets an artifact round-trip without carrying an
        enum object — and the stored form is always the word.

        A word this class does not name is a ``TypeError`` listing the members,
        because rendering it would produce SQL no database recognises (§6).
        """
        if isinstance(method, cls):
            return method.value
        if isinstance(method, str):
            for entry in cls:
                if entry.value == method:
                    return entry.value
        raise TypeError(
            "method must be a %s value or its string value, got %r; the members "
            "are %s" % (cls.__name__, method, [e.value for e in cls])
        )


@dataclass
class SubpartitionDefinition:
    """Base declaration for a single named subpartition.

    A backend-agnostic structural declaration. Backends add the boundary
    fields their syntax requires (Oracle's subpartition definitions carry
    ``less_than`` / ``in_values``; MySQL's carry only a name).

    Raises:
        ValueError: if ``name`` is empty or whitespace-only.
    """

    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("subpartition name must be a non-empty string")


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
    """

    name: str
    less_than: Optional[Sequence[BaseExpression]] = None
    in_values: Optional[Sequence[Union[BaseExpression, Sequence[BaseExpression]]]] = None
    subpartition_definitions: Optional[Sequence["SubpartitionDefinition"]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("partition name must be a non-empty string")
        if self.less_than is not None and self.in_values is not None:
            raise ValueError("less_than and in_values are mutually exclusive")


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

    #: The strategy vocabulary this clause speaks. A dialect with its own set
    #: substitutes it; the substitution must be a string enum (see
    #: :class:`PartitionStrategy`), because the normalised word is what renders
    #: and what travels.
    strategy_type: Type[Enum] = PartitionStrategy

    def __init__(
        self,
        dialect: "SQLDialectBase",
        method: Enum,
        keys: Sequence[BaseExpression],
    ):
        super().__init__(dialect)
        strategy = self.strategy_type
        # Accept the member or the word it spells: an artifact carries the word,
        # so a read must not need the enum object to get back. Whether the word
        # is one this clause knows is the *substituted* vocabulary's business,
        # not the caller's -- a backend that substitutes knows its own words.
        if isinstance(method, strategy):
            self.method = method.value
        elif isinstance(method, str) and any(e.value == method for e in strategy):
            self.method = method
        else:
            # Names the vocabulary and the words *it* defines. Deliberately not
            # the value: this message can reach a log, and a log is not where a
            # caller-supplied string belongs.
            raise TypeError(
                "method must be a %s value or its string value, got %s; the "
                "members are %s"
                % (strategy.__name__, type(method).__name__,
                   [e.value for e in strategy])
            )
        if not isinstance(self.method, str):
            # A value the vocabulary cannot spell is not a strategy. Caught here
            # rather than at render, because an unusable word in an artifact is
            # something the writer should hear about, not a reader (§6).
            raise TypeError(f"{strategy.__name__} values must be strings")
        if not keys:
            raise ValueError("keys are required")
        for key in keys:
            if not isinstance(key, BaseExpression):
                raise TypeError(
                    "keys must contain BaseExpression instances, "
                    f"got {type(key).__name__}"
                )
        self.keys = list(keys)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_partition_clause"

