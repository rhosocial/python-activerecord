# src/rhosocial/activerecord/backend/suggestion/dataclasses.py
"""Backend *suggestion* data classes.

A suggestion is the backend's answer to "how should this be declared/done here".
It is NOT an expression node and NOT a statement: it is a small immutable value
with a tri-state payload that a renderer turns into expressions. Suggestions
live in `backend.suggestion`, never in `backend.expression` (which is reserved
for `BaseExpression` derivatives only).

Each suggestion is a pure frozen dataclass with no methods; rendering is done
by the renderer classes in this package.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Tuple, Union

if TYPE_CHECKING:  # pragma: no cover
    from ..expression.bases import BaseExpression
    from ..expression.types._base import DataType


@dataclass(frozen=True)
class IntegerAutoIncrementColumnSuggestion:
    """A backend's suggested DDL for an integer auto-increment column.

    Attributes:
        type: The storage type expression (``IntegerType``, a backend's own
            integer subclass, or a pseudo-type such as PostgreSQL's SERIAL).
        auto_increment: How the value is generated on INSERT:
            - an expression node naming the mechanism the dialect renders;
            - ``False``: the type already absorbs the attribute, no further
              auto-increment clause may be added (SERIAL, SQLite rowid);
            - ``None``: no auto-increment (a plain integer type).
    """

    type: "DataType"
    auto_increment: Union["BaseExpression", bool, None] = None


@dataclass(frozen=True)
class PartitionBuildSuggestion:
    """Suggested action chain to declare a partitioned table at CREATE time."""

    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionAddSuggestion:
    """Suggested action chain to add/attach a partition to an existing table."""

    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionDropSuggestion:
    """Suggested action chain to drop/detach a partition from a table."""

    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionRetentionSuggestion:
    """Suggested action chain to retire old partitions (by cutoff)."""

    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionTableDropSuggestion:
    """Suggested action chain to drop the whole partitioned table."""

    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionTableAlterSuggestion:
    """Suggested action chain to alter the table's partitioning scheme."""

    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionSplitSuggestion:
    """Suggested action chain to split one partition into two."""

    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionMergeSuggestion:
    """Suggested action chain to merge two adjacent partitions."""

    operations: Union[Tuple["BaseExpression", ...], bool, None] = None
