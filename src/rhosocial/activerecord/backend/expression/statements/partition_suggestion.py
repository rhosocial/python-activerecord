# src/rhosocial/activerecord/backend/expression/statements/partition_suggestion.py
"""Backend *suggestion* data class for partition retirement.

A suggestion is the backend's answer to "how should old partitions be retired
here". It is not an expression node and not a statement: it is a small immutable
value the framework reads and turns into an ordered DDL action chain. The name
carries ``Suggestion`` (not ``Operation``) to mark it as a backend-suggested
value, matching ``IntegerAutoIncrementColumnSuggestion``.

Tri-state ``operations``:
- an ordered tuple of expression nodes -- apply them in order;
- ``False`` -- this strategy has no retirement mechanism on this backend;
- ``None`` -- no action needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Tuple, Union

if TYPE_CHECKING:  # pragma: no cover
    from ..bases import BaseExpression


@dataclass(frozen=True)
class PartitionRetentionSuggestion:
    """A backend's suggested action chain for retiring old partitions.

    Attributes:
        operations: Ordered expression nodes to apply in sequence; ``False``
            means this backend/strategy has no retirement mechanism (the caller
            reports it as unsupported); ``None`` means no action is needed.
    """

    operations: Union[Tuple["BaseExpression", ...], bool, None] = None
