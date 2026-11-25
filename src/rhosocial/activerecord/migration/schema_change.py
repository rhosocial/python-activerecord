# src/rhosocial/activerecord/migration/schema_change.py
"""ActiveRecord-layer schema change: model-declaration diff → ALTER statements.

Layer position (layer-separation.md): migration is an $\\mathcal{A}$-side
component. This module reads model declarations (AR concepts) and produces
backend *expression instances* through the negotiated contract $\\mathcal{I}$ —
backend stays ignorant of AR (A1/A2). It never imports ``base`` from backend.

Mechanism split (backend-expression-dialect-suggestion.md §3.4):

* **Syntax-level, single-action changes** (add/drop column, rename, plain type
  change) belong to the expression–dialect system. This module emits the
  appropriate core ``AlterTableAction`` expressions directly; a dialect that
  cannot render one fails fast at format time (capability stays in $\\mathcal{B}$,
  invisible to $\\mathcal{A}$ — activerecord-migration.md §1).
* **Multi-step strategy changes** (table rebuild, data-preserving type change,
  add-NOT-NULL-with-backfill, partition ops) are decision points $\\delta$ that
  must be resolved by a *backend suggestion* via $\\mathcal{I}$. This module only
  identifies and describes them in frozen, dialect-neutral suggestion-point
  objects; it does not hard-code a strategy or render any SQL.

Rename pairing (data-loss stopgap)
----------------------------------

``diff_declarations`` is name-keyed, so a pure column rename otherwise looks
like a drop plus an add. It recognises a rename **only** when a table has
exactly one removal and exactly one addition and their complete declarations
(except the name) are equivalent. Ambiguous cases, and any case where either
side carries a data-affecting change, deliberately stay drop+add: losing a
rename is recoverable (a manual migration), while guessing one wrongly can
silently discard data. A source that gains an explicit rename declaration
(``column_renames()``) is preferred over this heuristic. ``RENAME`` already
existed in the diff vocabulary and is reused as-is.

Next step (not in this module)
------------------------------

Consumption of the suggestion points is intentionally left out: a concrete
backend must first implement the matching ``suggest_*`` protocol, then a
consumer decides what to do with the tri-state answer. Core only freezes the
contract here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING

from ..backend.schema.differ import ColumnChangeKind, SchemaDiff, TableDiff
from ..backend.suggestion.definitions import (
    ColumnReorderSuggestion,
    PartitionSchemeChangeSuggestion,
    SuggestionPoint,
    TableConstraintChangeSuggestion,
    TableIndexChangeSuggestion,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..base.ddl import ModelDDLDeclaration


@dataclass
class FieldChange:
    """The comparable declaration of one field (lightweight, dialect-free)."""

    name: str
    python_type: Any = None
    declared_type: Any = None
    constraints: Sequence[Any] = field(default_factory=tuple)
    attributes: Sequence[Any] = field(default_factory=tuple)
    comment: Optional[str] = None
    has_identity: bool = False
    index_names: Sequence[str] = field(default_factory=tuple)

    def signature(self) -> tuple:
        return (
            self.python_type,
            _freeze(self.declared_type),
            tuple(_freeze(c) for c in self.constraints),
            tuple(_freeze(a) for a in self.attributes),
            self.comment,
            self.has_identity,
            tuple(self.index_names),
        )


def _freeze(value: Any) -> Any:
    """Comparable form of a declaration value, without rendering SQL."""
    if value is None or isinstance(value, (str, int, float, bool, bytes, tuple)):
        return value
    getter = getattr(value, "get_params", None)
    if callable(getter):
        try:
            return ("params", _freeze(getter()))
        except Exception:  # pragma: no cover
            pass
    if isinstance(value, (list, set, frozenset)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((str(k), _freeze(v)) for k, v in value.items()))
    return ("repr", repr(value))


def _field_change(source: "ModelDDLDeclaration", field_name: str) -> FieldChange:
    from ..base.derivation import _has_declared_identity

    return FieldChange(
        name=source.column_name(field_name),
        python_type=source.field_python_type(field_name),
        declared_type=source.column_data_type(field_name),
        constraints=tuple(source.column_constraints(field_name)),
        attributes=tuple(source.column_attributes(field_name)),
        comment=source.column_comment(field_name),
        has_identity=_has_declared_identity(source, field_name),
        index_names=tuple(idx.name for idx in source.column_indexes(field_name)),
    )


def _explicit_rename_pairs(source: "ModelDDLDeclaration") -> Dict[str, str]:
    """Declared old→new column names, if the source exposes such a signal.

    ``ModelDDLDeclaration`` has no rename declaration today, so this is an
    extension point rather than a live path: a source that later adds
    ``column_renames()`` is preferred over the signature heuristic, and an
    explicit answer is honoured only when it too passes the equivalence guard.
    """
    getter = getattr(source, "column_renames", None)
    if not callable(getter):
        return {}
    try:
        return {str(old): str(new) for old, new in dict(getter()).items()}
    except (TypeError, ValueError):  # pragma: no cover - malformed declaration
        return {}


def diff_declarations(
    old_source: "ModelDDLDeclaration",
    new_source: "ModelDDLDeclaration",
) -> SchemaDiff:
    """Compare two ActiveRecord models field-by-field, table-by-table.

    Produces the dialect-neutral :class:`SchemaDiff`; each ``ColumnDiff.old/new``
    carries a :class:`FieldChange`. This is the field-by-field, table-by-table
    planning input — no introspection snapshot involved.
    """
    # key by column name for matching
    old_by_name = {
        fc.name: fc
        for fc in (_field_change(old_source, n) for n in old_source.ddl_field_names())
    }
    new_by_name = {
        fc.name: fc
        for fc in (_field_change(new_source, n) for n in new_source.ddl_field_names())
    }

    diff = SchemaDiff(dialect_class="activerecord.declaration")
    table_name = new_source.table_name()
    td = TableDiff(table_name=table_name, old=old_source, new=new_source)

    removals = sorted(set(old_by_name) - set(new_by_name))
    additions = sorted(set(new_by_name) - set(old_by_name))

    # Conservative pairing: one removal and one addition, equivalent on every
    # declared fact except the name. Anything else stays drop+add (see module
    # docstring for why that trade-off favours data safety).
    rename_pairs: Dict[str, str] = {}
    explicit = _explicit_rename_pairs(new_source) or _explicit_rename_pairs(old_source)
    if explicit:
        for old_name, new_name in explicit.items():
            if (
                old_name in removals
                and new_name in additions
                and old_by_name[old_name].signature() == new_by_name[new_name].signature()
            ):
                rename_pairs[old_name] = new_name
    elif len(removals) == 1 and len(additions) == 1:
        old_name, new_name = removals[0], additions[0]
        if old_by_name[old_name].signature() == new_by_name[new_name].signature():
            rename_pairs[old_name] = new_name

    renamed_targets = set(rename_pairs.values())
    for name in removals:
        if name in rename_pairs:
            new_name = rename_pairs[name]
            td.column_diffs.append(
                __column_diff(
                    name, old_by_name[name], new_by_name[new_name],
                    ColumnChangeKind.RENAME, new_name=new_name,
                )
            )
        else:
            td.column_diffs.append(
                __column_diff(name, old_by_name[name], None, ColumnChangeKind.DROP)
            )
    for name in additions:
        if name not in renamed_targets:
            td.column_diffs.append(
                __column_diff(name, None, new_by_name[name], ColumnChangeKind.ADD)
            )
    for name in set(old_by_name) & set(new_by_name):
        of, nf = old_by_name[name], new_by_name[name]
        if of.signature() != nf.signature():
            td.column_diffs.append(
                __column_diff(name, of, nf, ColumnChangeKind.MODIFY)
            )

    old_order = [old_source.column_name(n) for n in old_source.ddl_field_names()]
    new_order = [new_source.column_name(n) for n in new_source.ddl_field_names()]
    common_new = [n for n in new_order if n in old_by_name]
    common_old = [n for n in old_order if n in new_by_name]
    td.reordered_columns = [
        n for n in common_new if common_new.index(n) != common_old.index(n)
    ]
    td.comment_changed = any(
        of.comment != new_by_name[k].comment
        for k, of in old_by_name.items() if k in new_by_name
    )
    # Table-level constraint/index/partition differences signal a multi-step
    # decision point; their concrete strategy comes from a backend suggestion.
    td.constraints_changed = _freeze(old_source.table_constraints()) != _freeze(
        new_source.table_constraints()
    )
    td.indexes_changed = _freeze(old_source.table_indexes()) != _freeze(
        new_source.table_indexes()
    )
    td.partition_changed = _freeze(old_source.table_partition()) != _freeze(
        new_source.table_partition()
    )

    if td.has_changes:
        diff.table_diffs[table_name] = td
    return diff


def __column_diff(name, old, new, kind, new_name=None):
    from ..backend.schema.differ import ColumnDiff

    return ColumnDiff(name, old, new, kind=kind, new_name=new_name)


@dataclass
class ChangePlan:
    """Result of planning a schema change.

    ``statements`` are core ALTER expressions (one action each), ready for
    ``MigrationContext.apply``. ``suggestion_points`` are frozen, dialect-neutral
    decision objects the user resolves by asking the backend (via
    $\\mathcal{I}$); AR does not hard-code their strategy. Each object still
    compares equal to its old bare label for caller compatibility.
    """

    statements: List[Any] = field(default_factory=list)
    suggestion_points: List["SuggestionPoint"] = field(default_factory=list)
    diff: Optional[SchemaDiff] = None

    @property
    def has_changes(self) -> bool:
        return bool(self.statements) or bool(self.suggestion_points)


def plan_changes(
    old_source: "ModelDDLDeclaration",
    new_source: "ModelDDLDeclaration",
    dialect: Any,
) -> ChangePlan:
    """Plan an old→new schema change.

    Single-action changes become core ALTER expressions directly (syntax-level,
    expression–dialect system). Multi-step changes are recorded as suggestion
    points to resolve via a backend suggestion contract, never hard-coded here.
    """
    from ..base.derivation import build_column_definitions
    from ..backend.expression.statements.ddl_alter import (
        AddColumnAction, DropColumnAction, RenameColumnAction, AlterTableStatement,
    )
    from ..backend.expression.objects import Table

    diff = diff_declarations(old_source, new_source)
    plan = ChangePlan(diff=diff)

    new_columns = {c.name: c for c in build_column_definitions(new_source, dialect)}
    td = diff.table_diffs.get(new_source.table_name())
    if td is None:
        return plan
    table = Table(dialect, td.table_name)

    for cd in sorted(td.column_diffs, key=lambda d: d.column_name):
        if cd.kind is ColumnChangeKind.ADD:
            col = new_columns.get(cd.column_name)
            if col is not None:
                plan.statements.append(
                    AlterTableStatement(dialect, table, [AddColumnAction(dialect, col)])
                )
        elif cd.kind is ColumnChangeKind.DROP:
            plan.statements.append(
                AlterTableStatement(dialect, table, [DropColumnAction(dialect, cd.column_name)])
            )
        elif cd.kind is ColumnChangeKind.MODIFY:
            # Plain type change is syntax-level (expression system). Emit the
            # neutral core expression; the dialect formatter decides the spelling
            # and fails fast if it cannot render it (capability stays in B).
            # Choosing a backend-specific class here would leak B knowledge into A.
            from ..backend.expression.statements.ddl_alter import (
                AlterColumnAction, ColumnAlterOperation,
            )

            col = new_columns.get(cd.column_name)
            if col is not None and col.data_type is not None:
                plan.statements.append(
                    AlterTableStatement(
                        dialect,
                        table,
                        [AlterColumnAction(
                            dialect, cd.column_name,
                            operation=ColumnAlterOperation.SET_DATA_TYPE,
                            new_value=col.data_type,
                        )],
                    )
                )
        elif cd.kind is ColumnChangeKind.RENAME and cd.new_name:
            # A confidently paired rename is a single syntax-level action: the
            # neutral core expression carries the old and new names, and the
            # dialect formatter decides whether it can render it.
            plan.statements.append(
                AlterTableStatement(
                    dialect,
                    table,
                    [RenameColumnAction(
                        dialect, old_name=cd.column_name, new_name=cd.new_name,
                    )],
                )
            )

    if td.reordered_columns:
        old_order = tuple(
            old_source.column_name(n) for n in old_source.ddl_field_names()
        )
        new_order = tuple(
            new_source.column_name(n) for n in new_source.ddl_field_names()
        )
        plan.suggestion_points.append(
            ColumnReorderSuggestion(
                table_name=td.table_name,
                old_order=old_order,
                new_order=new_order,
                reordered_columns=tuple(td.reordered_columns),
            )
        )
    if td.constraints_changed:
        plan.suggestion_points.append(
            TableConstraintChangeSuggestion(
                table_name=td.table_name,
                old_constraints=tuple(_freeze(c) for c in old_source.table_constraints()),
                new_constraints=tuple(_freeze(c) for c in new_source.table_constraints()),
            )
        )
    if td.indexes_changed:
        plan.suggestion_points.append(
            TableIndexChangeSuggestion(
                table_name=td.table_name,
                old_indexes=tuple(_freeze(i) for i in old_source.table_indexes()),
                new_indexes=tuple(_freeze(i) for i in new_source.table_indexes()),
            )
        )
    if td.partition_changed:
        plan.suggestion_points.append(
            PartitionSchemeChangeSuggestion(
                table_name=td.table_name,
                old_partition=_freeze(old_source.table_partition()),
                new_partition=_freeze(new_source.table_partition()),
            )
        )
    return plan
