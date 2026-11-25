# src/rhosocial/activerecord/backend/suggestion/definitions/change_plan.py
"""Frozen suggestion points for the four multi-step migration change points.

These are the data shapes of the negotiated contract $\\mathcal{I}$ for the
decision points an $\\mathcal{A}$-side planner cannot resolve on its own:
column reorder, table constraint change, table index change and partition
scheme change. They deliberately follow ``definitions/partition.py``:

* a frozen dataclass value, with no renderer and no SQL;
* ``operations`` is tri-state -- a tuple of *existing* expression instances
  (a backend-supported action chain), ``False`` (the backend cannot address
  the change automatically), or ``None`` (no action / no protocol answer);
* the context fields are dialect-neutral, so a backend can decide what to
  answer without the core knowing any backend vocabulary.

Two kinds of context are carried side by side:

* the original minimal frozen projections (``reordered_columns``,
  ``old_constraints`` / ``new_constraints``, ``old_indexes`` / ``new_indexes``,
  ``old_partition`` / ``new_partition``) stay exactly as they were, for callers
  that only need a label or a comparable shape;
* optional *live declaration* projections (``old_fields`` / ``new_fields``,
  ``old_constraint_declarations`` / ``new_constraint_declarations``,
  ``old_index_declarations`` / ``new_index_declarations``,
  ``old_partition_declaration`` / ``new_partition_declaration``) carry the
  model's own expression artifacts. They keep the information a frozen
  projection throws away: the full ``ColumnDefinition`` (type, constraints,
  attributes) needed to render ``MODIFY COLUMN ... FIRST|AFTER``, the
  ``TableConstraint.branch`` class that distinguishes ``PRIMARY KEY`` from
  ``UNIQUE``, and a real ``IndexDefinition`` whose column expressions and
  predicate survive. No SQL is serialized and no expression class is invented
  here -- the backend receives the same objects the declaration surface holds.

Consumption of these values by a concrete backend is intentionally **not**
implemented in this module. Core declares only the contract; the next step is
for each backend to implement the matching ``suggest_*`` protocol and for a
consumer to gate on ``isinstance`` (a backend that does not implement the
protocol is structurally absent, not explicitly unsupported).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence, Tuple, Union

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.bases import BaseExpression
    from ...expression.statements.ddl_partition import PartitionClause
    from ...expression.statements.ddl_table import (
        ColumnDefinition,
        IndexDefinition,
        TableConstraint,
    )


Operations = Union[Tuple["BaseExpression", ...], bool, None]


class _LabelledPoint:
    """Shared behaviour for a suggestion point.

    ``ChangePlan.suggestion_points`` used to hold bare label strings. Keeping
    ``point == "column_reorder"`` true lets older callers and tests keep working
    while the payload becomes a data object; ``state`` names the tri-state
    without bundling an outcome class into the contract.
    """

    label: str

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.label == other
        return self is other

    __hash__ = object.__hash__

    @property
    def state(self) -> str:
        """One of ``actions`` / ``unaddressable`` / ``absent``."""
        operations = getattr(self, "operations", None)
        if isinstance(operations, tuple):
            return "actions"
        if operations is False:
            return "unaddressable"
        return "absent"


@dataclass(frozen=True, eq=False)
class ColumnReorderSuggestion(_LabelledPoint):
    """Decision point: a table's column order changed between declarations."""

    label: str = "column_reorder"
    table_name: str = ""
    old_order: Tuple[str, ...] = ()
    new_order: Tuple[str, ...] = ()
    reordered_columns: Tuple[str, ...] = ()
    operations: Operations = None
    # Live typed column declarations keyed by column name. A backend that can
    # reorder non-destructively needs the whole column specification, not only
    # the names in ``old_order`` / ``new_order``.
    old_fields: Mapping[str, "ColumnDefinition"] = field(
        default_factory=lambda: MappingProxyType({})
    )
    new_fields: Mapping[str, "ColumnDefinition"] = field(
        default_factory=lambda: MappingProxyType({})
    )


@dataclass(frozen=True, eq=False)
class TableConstraintChangeSuggestion(_LabelledPoint):
    """Decision point: a table's constraints changed between declarations."""

    label: str = "table_constraint_change"
    table_name: str = ""
    old_constraints: Tuple[Any, ...] = ()
    new_constraints: Tuple[Any, ...] = ()
    operations: Operations = None
    # Live ``TableConstraint`` declarations. Their ``branch`` keeps the kind
    # (``PRIMARY KEY`` vs ``UNIQUE``) that ``_freeze()`` collapses into one
    # ``{"columns": ...}`` projection, so a backend can build a real
    # ``AddTableConstraintAction`` instead of refusing to guess.
    old_constraint_declarations: Tuple["TableConstraint", ...] = ()
    new_constraint_declarations: Tuple["TableConstraint", ...] = ()


@dataclass(frozen=True, eq=False)
class TableIndexChangeSuggestion(_LabelledPoint):
    """Decision point: a table's indexes changed between declarations."""

    label: str = "table_index_change"
    table_name: str = ""
    old_indexes: Tuple[Any, ...] = ()
    new_indexes: Tuple[Any, ...] = ()
    operations: Operations = None
    # Live ``IndexDefinition`` declarations. A frozen column expression or a
    # predicate cannot be rebuilt into a real index clause; the live object can.
    old_index_declarations: Tuple["IndexDefinition", ...] = ()
    new_index_declarations: Tuple["IndexDefinition", ...] = ()


@dataclass(frozen=True, eq=False)
class PartitionSchemeChangeSuggestion(_LabelledPoint):
    """Decision point: a table's partitioning scheme changed."""

    label: str = "partition_scheme_change"
    table_name: str = ""
    old_partition: Any = None
    new_partition: Any = None
    operations: Operations = None
    # The live ``table_partition()`` value (a ``PartitionClause`` or a sequence
    # of them), kept as returned rather than reduced to a comparable tuple.
    old_partition_declaration: Optional[
        Union["PartitionClause", Sequence["PartitionClause"]]
    ] = None
    new_partition_declaration: Optional[
        Union["PartitionClause", Sequence["PartitionClause"]]
    ] = None


SuggestionPoint = Union[
    ColumnReorderSuggestion,
    TableConstraintChangeSuggestion,
    TableIndexChangeSuggestion,
    PartitionSchemeChangeSuggestion,
]


__all__ = [
    "ColumnReorderSuggestion",
    "TableConstraintChangeSuggestion",
    "TableIndexChangeSuggestion",
    "PartitionSchemeChangeSuggestion",
    "SuggestionPoint",
]
