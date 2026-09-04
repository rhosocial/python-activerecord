# src/rhosocial/activerecord/backend/expression/statements/ddl_diff.py
"""Expression-level CREATE TABLE diff: plan dataclasses.

The diff pipeline (Phase 3 of the "derive DDL from ActiveRecord" plan)
compares two ``CreateTableExpression`` instances and produces a plan that
transforms the old shape into the new one:

- ``DiffPlan.alters``  — ordered ``AlterTableExpression`` statements for
  changes expressible as in-place ALTERs.
- ``DiffPlan.rebuild`` — a ``RebuildPlan`` for changes that cannot be
  expressed as pure ALTERs (column type changes on SQLite, primary key
  changes, partition changes, ...): create a new-definition table under a
  temporary name, copy surviving rows, drop the old table, rename the new
  one to the final name.

The two fields are mutually exclusive: ``rebuild is None`` iff ``alters``
may be non-empty. When ``rebuild`` is set, data copying is the caller's
responsibility (see the migration plan, topic 3.3 — data migration is a
follow-up topic).

The comparison logic itself lives in the dialect layer
(``CreateTableExpressionDiffSupport`` protocol + ``CreateTableExpressionDiffMixin``
generic implementation), because equivalence rules and rebuild thresholds
are backend policy.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .ddl_alter import AlterTableExpression
from .ddl_table import CreateTableExpression, DropTableExpression


@dataclass
class RebuildPlan:
    """Structural rebuild plan for changes not expressible as pure ALTERs.

    Execution order (structural steps only — the data copy is the
    caller's step 2):

    1. ``create``   — create the new-definition table under ``temp_table_name``
    2. (caller)     — copy data: ``INSERT INTO temp (copy_columns)
                       SELECT copy_columns FROM old_table``
    3. ``drop_old`` — drop the original table
    4. ``rename``   — rename the temp table to the final name

    ``rename`` is a single ``RenameTable`` action wrapped in its own
    ``AlterTableExpression`` because SQLite executes one action per
    statement.
    """

    create: CreateTableExpression
    drop_old: DropTableExpression
    rename: AlterTableExpression
    temp_table_name: str = ""
    copy_columns: List[str] = field(default_factory=list)
    reason: str = ""

    def ordered_statements(self) -> List[object]:
        """Structural statements in execution order (data copy is the caller's step 2)."""
        return [self.create, self.drop_old, self.rename]


@dataclass
class DiffPlan:
    """Result of comparing two ``CreateTableExpression`` instances.

    Exactly one of ``alters`` / ``rebuild`` is meaningful:

    - ``rebuild is None`` → ``alters`` carries the (possibly empty) list of
      ALTER TABLE statements.
    - ``rebuild is not None`` → ``alters`` is empty; the table must be
      rebuilt structurally.

    ``notes`` carries non-fatal explanatory messages (e.g. which change
    forced a rebuild) for caller diagnostics; it never affects semantics.
    """

    alters: List[AlterTableExpression] = field(default_factory=list)
    rebuild: Optional[RebuildPlan] = None
    notes: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.rebuild is not None and self.alters:
            raise ValueError(
                "DiffPlan.alters and DiffPlan.rebuild are mutually exclusive: "
                "alters must be empty when a rebuild is planned"
            )

    @property
    def has_changes(self) -> bool:
        if self.rebuild is not None:
            return True
        return any(a.actions for a in self.alters)
