# src/rhosocial/activerecord/backend/schema/alter_planner.py
"""Turn a model-declaration diff into an executable ALTER plan.

The planner is the bridge between ``DeclarationDiffer`` (what changed) and the
expression layer (the ALTER actions that apply it). It enforces two rules:

* **One expression = one SQL statement.** Each action becomes its own
  ``AlterTableStatement``; the plan is an ordered list of them, never a single
  multiline/semicolon-joined string.
* **Capability truth, not probe optimism.** A change is emitted in place only
  when the dialect can actually render it; otherwise it is routed to a rebuild.

All expressions used here come from ``backend.expression.statements`` (reuse,
never invent). Capability checks happen via the dialect's ``supports_*`` and,
for type changes, the backend's ``alter_column_type_action`` hook.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, TYPE_CHECKING

from .differ import ColumnChangeKind, SchemaDiff, TableDiff
from .declaration_diff import DeclarationDiffer

if TYPE_CHECKING:  # pragma: no cover
    from ...base.ddl import ModelDDLDeclaration


@dataclass
class RebuildPlan:
    """A table rebuild for changes that cannot be expressed as in-place ALTER.

    A rebuild is an ordered multi-step operation owned by the migration layer;
    this value only records *which* table and *why* — it carries no SQL (the
    migration planner fills in the dialect-specific create/copy/swap steps).
    """

    table_name: str
    reason: str


@dataclass
class AlterPlan:
    """The result of planning an old→new schema change.

    ``statements`` are independent, ordered, each carrying one action.
    ``rebuilds`` are tables that must be rebuilt instead of altered.
    """

    statements: List[Any] = field(default_factory=list)
    rebuilds: List[RebuildPlan] = field(default_factory=list)
    diff: Optional[SchemaDiff] = None

    @property
    def has_changes(self) -> bool:
        return bool(self.statements) or bool(self.rebuilds)

    @property
    def is_empty(self) -> bool:
        return not self.has_changes


class AlterPlanner:
    """Plan an ALTER sequence from two ActiveRecord model declarations."""

    def plan(
        self,
        old_source: "ModelDDLDeclaration",
        new_source: "ModelDDLDeclaration",
        dialect: Any,
    ) -> AlterPlan:
        diff = DeclarationDiffer().compare(old_source, new_source, dialect)
        plan = AlterPlan(diff=diff)

        for td in diff.table_diffs.values():
            if td.is_added or td.is_removed:
                # create/drop table is the migration layer's job, not ALTER.
                continue
            self._plan_table(td, old_source, new_source, dialect, plan)
        return plan

    def _plan_table(
        self,
        td: TableDiff,
        old_source: "ModelDDLDeclaration",
        new_source: "ModelDDLDeclaration",
        dialect: Any,
        plan: AlterPlan,
    ) -> None:
        from ...base.derivation import build_column_definitions

        new_columns = {
            c.name: c for c in build_column_definitions(new_source, dialect)
        }
        supports_rename = _probe(dialect, "supports_rename_column", default=True)
        supports_drop = _probe(dialect, "supports_drop_column", default=True)

        for cd in sorted(td.column_diffs, key=lambda d: d.column_name):
            if cd.kind is ColumnChangeKind.ADD:
                col = new_columns.get(cd.column_name)
                if col is not None:
                    from ...backend.expression.statements.ddl_alter import AddColumnAction

                    plan.statements.append(_one_action(dialect, td.table_name, AddColumnAction(dialect, col)))

            elif cd.kind is ColumnChangeKind.DROP:
                if supports_drop:
                    from ...backend.expression.statements.ddl_alter import DropColumnAction

                    plan.statements.append(
                        _one_action(dialect, td.table_name, DropColumnAction(dialect, cd.column_name))
                    )
                else:
                    plan.rebuilds.append(
                        RebuildPlan(td.table_name, "DROP COLUMN not supported in place")
                    )

            elif cd.kind is ColumnChangeKind.RENAME and cd.new_name:
                if supports_rename:
                    from ...backend.expression.statements.ddl_alter import RenameColumnAction

                    plan.statements.append(
                        _one_action(
                            dialect, td.table_name,
                            RenameColumnAction(dialect, cd.column_name, cd.new_name),
                        )
                    )
                else:
                    plan.rebuilds.append(
                        RebuildPlan(td.table_name, "RENAME COLUMN not supported in place")
                    )

            elif cd.kind is ColumnChangeKind.MODIFY:
                self._plan_modify(cd, td, new_columns, dialect, plan)

        if td.reordered_columns:
            plan.rebuilds.append(
                RebuildPlan(td.table_name, "column reorder requires rebuild")
            )
        if td.comment_changed or td.table_options_changed or td.requires_rebuild:
            plan.rebuilds.append(
                RebuildPlan(
                    td.table_name,
                    td.rebuild_reason or "table-level change not expressible as ALTER",
                )
            )

    def _plan_modify(self, cd, td, new_columns, dialect, plan) -> None:
        """Plan a column type/property change via the backend hook, else rebuild."""
        col = new_columns.get(cd.column_name)
        hook = getattr(dialect, "alter_column_type_action", None)
        if col is None or not callable(hook):
            plan.rebuilds.append(
                RebuildPlan(td.table_name, f"no in-place action for {cd.column_name}")
            )
            return
        action = hook(_decl_to_col(cd.old, dialect), col)
        if action is None:
            plan.rebuilds.append(
                RebuildPlan(td.table_name, f"backend declined type change for {cd.column_name}")
            )
            return
        plan.statements.append(_one_action(dialect, td.table_name, action))


def _probe(dialect: Any, name: str, *, default: bool) -> bool:
    fn = getattr(dialect, name, None)
    if not callable(fn):
        return default
    try:
        return bool(fn())
    except Exception:  # pragma: no cover
        return default


def _one_action(dialect: Any, table_name: str, action: Any) -> Any:
    """Wrap one action in its own AlterTableStatement (1:1 with SQL)."""
    from ...backend.expression.objects import Table
    from ...backend.expression.statements.ddl_alter import AlterTableStatement

    return AlterTableStatement(dialect, Table(dialect, table_name), [action])


def _decl_to_col(decl: Any, dialect: Any) -> Any:
    """Best-effort conversion of a FieldDeclaration into a ColumnDefinition.

    The backend type-change hooks are written against column definitions; the
    declaration payload carries the facts to reconstruct one where needed.
    Returns None when the declaration is not convertible.
    """
    if decl is None:
        return None
    from ...backend.expression.statements import ColumnDefinition
    from ...backend.expression.types import IntegerType

    data_type = decl.declared_type
    if not hasattr(data_type, "to_sql"):
        # A UseSqlType marker or a python type: fall back to a neutral integer
        # type; the hook mostly needs the new column, not the old one's type.
        data_type = IntegerType(dialect=dialect)
    return ColumnDefinition(dialect, decl.name, data_type)
