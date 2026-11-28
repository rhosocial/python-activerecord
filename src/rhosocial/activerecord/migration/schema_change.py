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
  objects; it does not hard-code a strategy or render any SQL. Each point keeps
  both its original minimal projection and optional *live declaration* context
  (full ``ColumnDefinition``, ``TableConstraint``, ``IndexDefinition``,
  ``PartitionClause``) so a capable backend can build a real action instead of
  refusing for lack of information.

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

Consumption (explicit, see :func:`resolve_suggestions`)
-------------------------------------------------------

Planning only *describes* the decision points. A separate, caller-invoked step
resolves them against a dialect that implements the matching ``suggest_*``
protocol. That step appends the backend's expressions to the executable
statement list and reports every tri-state answer (actions / explicit
unsupported / no-answer / missing protocol) without ever rendering SQL or
inventing an expression type on this side. ``plan_changes`` itself is unchanged.

Equivalence normalisation (what "the same" means)
-------------------------------------------------

A declared type is compared with its spacing collapsed (``DECIMAL(10, 2)`` and
``DECIMAL(10,2)`` are one type); nothing else about it is rewritten. Case is
**not** folded and literals inside a declaration are **not** touched, because a
type declaration can carry case-bearing text such as ``ENUM('a','b')``. The
asymmetry is deliberate: a false *inequality* produces one extra MODIFY, while a
false *equality* would silently skip a real change. Free comment text is
compared verbatim for the same reason.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

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
    column_options: Sequence[Any] = field(default_factory=tuple)

    def signature(self) -> tuple:
        """A frozen projection of every declared fact this field carries.

        Column options are encoded dialect-neutrally as
        ``(option class name, frozen option state)``, where the state is the
        option's own ``__dict__`` (or ``__slots__``) flattened to sorted
        ``(attribute, frozen value)`` pairs.  A change to any option field --
        a charset, a column format, a storage mode -- therefore counts as a
        declaration change even when the SQL type is unchanged.
        """
        return (
            self.python_type,
            _freeze(self.declared_type),
            tuple(_freeze(c) for c in self.constraints),
            tuple(_freeze(a) for a in self.attributes),
            self.comment,
            self.has_identity,
            tuple(self.index_names),
            tuple(_freeze_column_option(o) for o in self.column_options),
        )


def _freeze(value: Any) -> Any:
    """Comparable form of a declaration value, without rendering SQL."""
    if value is None or isinstance(value, (str, int, float, bool, bytes, tuple)):
        return value
    if isinstance(value, Enum):
        return ("enum", type(value).__name__, value.name)
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


def _freeze_column_option(option: Any) -> tuple:
    """The dialect-neutral comparable form of one declared column option.

    Encoding: ``(type(option).__name__, state)``.  ``state`` is the option's
    own instance state -- its ``__dict__`` items, or its ``__slots__`` values,
    sorted by attribute name and each frozen through :func:`_freeze`.  Using
    the class name plus state rather than ``repr`` keeps the projection stable
    across processes: the default object repr embeds an address and would make
    every comparison of two otherwise identical declarations report a change.
    """
    state = getattr(option, "__dict__", None)
    if isinstance(state, dict) and state:
        return (
            type(option).__name__,
            tuple(sorted((str(k), _freeze(v)) for k, v in state.items())),
        )
    getter = getattr(option, "get_params", None)
    if callable(getter):
        return (type(option).__name__, ("params", _freeze(getter())))
    slots = getattr(type(option), "__slots__", ())
    if isinstance(slots, str):
        slots = (slots,)
    slot_state = tuple(
        (name, _freeze(getattr(option, name))) for name in slots if hasattr(option, name)
    )
    return (
        type(option).__name__,
        tuple(sorted(slot_state)),
    )


def _field_change(source: "ModelDDLDeclaration", field_name: str) -> FieldChange:
    from ..base.derivation import _has_declared_identity, _normalise_column_options

    return FieldChange(
        name=source.column_name(field_name),
        python_type=source.field_python_type(field_name),
        declared_type=source.column_data_type(field_name),
        constraints=tuple(source.column_constraints(field_name)),
        attributes=tuple(source.column_attributes(field_name)),
        comment=source.column_comment(field_name),
        has_identity=_has_declared_identity(source, field_name),
        index_names=tuple(idx.name for idx in source.column_indexes(field_name)),
        column_options=_normalise_column_options(source, field_name),
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
    # Private bookkeeping so explicit resolution is one-shot per point.
    _resolved_point_ids: set = field(default_factory=set, repr=False, compare=False)

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
    from ..backend.expression.statements import (
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
                    AlterTableStatement(dialect, table, AddColumnAction(dialect, col))
                )
        elif cd.kind is ColumnChangeKind.DROP:
            plan.statements.append(
                AlterTableStatement(dialect, table, DropColumnAction(dialect, cd.column_name))
            )
        elif cd.kind is ColumnChangeKind.MODIFY:
            # Plain type change is syntax-level (expression system). Emit the
            # neutral core expression; the dialect formatter decides the spelling
            # and fails fast if it cannot render it (capability stays in B).
            # Choosing a backend-specific class here would leak B knowledge into A.
            from ..backend.expression.statements import (
                AlterColumnAction, ColumnAlterOperation,
            )

            col = new_columns.get(cd.column_name)
            if col is not None and col.data_type is not None:
                plan.statements.append(
                    AlterTableStatement(
                        dialect,
                        table,
                        AlterColumnAction(
                            dialect, cd.column_name,
                            operation=ColumnAlterOperation.SET_DATA_TYPE,
                            new_value=col.data_type,
                        ),
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
                    RenameColumnAction(
                        dialect, old_name=cd.column_name, new_name=cd.new_name,
                    ),
                )
            )

    if td.reordered_columns:
        old_order = tuple(
            old_source.column_name(n) for n in old_source.ddl_field_names()
        )
        new_order = tuple(
            new_source.column_name(n) for n in new_source.ddl_field_names()
        )
        # The name-only projections above cannot tell a backend how to rebuild
        # a column for MODIFY COLUMN ... FIRST|AFTER. build_column_definitions
        # resolves the same declarations already used for ADD/MODIFY statements,
        # keyed by database column name, so the full typed spec travels with
        # the point without any backend vocabulary entering A.
        old_fields = {
            column.name: column
            for column in build_column_definitions(old_source, dialect)
        }
        plan.suggestion_points.append(
            ColumnReorderSuggestion(
                table_name=td.table_name,
                old_order=old_order,
                new_order=new_order,
                reordered_columns=tuple(td.reordered_columns),
                old_fields=MappingProxyType(old_fields),
                new_fields=MappingProxyType(new_columns),
            )
        )
    if td.constraints_changed:
        old_decls = tuple(old_source.table_constraints())
        new_decls = tuple(new_source.table_constraints())
        plan.suggestion_points.append(
            TableConstraintChangeSuggestion(
                table_name=td.table_name,
                old_constraints=tuple(_freeze(c) for c in old_decls),
                new_constraints=tuple(_freeze(c) for c in new_decls),
                old_constraint_declarations=old_decls,
                new_constraint_declarations=new_decls,
            )
        )
    if td.indexes_changed:
        old_decls = tuple(old_source.table_indexes())
        new_decls = tuple(new_source.table_indexes())
        plan.suggestion_points.append(
            TableIndexChangeSuggestion(
                table_name=td.table_name,
                old_indexes=tuple(_freeze(i) for i in old_decls),
                new_indexes=tuple(_freeze(i) for i in new_decls),
                old_index_declarations=old_decls,
                new_index_declarations=new_decls,
            )
        )
    if td.partition_changed:
        old_decl = old_source.table_partition()
        new_decl = new_source.table_partition()
        plan.suggestion_points.append(
            PartitionSchemeChangeSuggestion(
                table_name=td.table_name,
                old_partition=_freeze(old_decl),
                new_partition=_freeze(new_decl),
                old_partition_declaration=old_decl,
                new_partition_declaration=new_decl,
            )
        )
    return plan


# -- Suggestion consumption -------------------------------------------------
#
# The A side resolves a frozen point by asking a dialect through the matching
# minimal protocol. It never renders SQL and never constructs an expression
# type: the chain it appends is exactly the one the backend returned. Every
# answer is recorded, so ``False`` (explicit unsupported) is never collapsed
# into ``None`` (no answer), and a dialect missing the protocol is reported
# rather than silently treated as "nothing to do".


#: (protocol class name, suggest method name) keyed by frozen point type.
_CHANGE_SUGGESTION_PROTOCOLS = {
    ColumnReorderSuggestion: ("ColumnReorderSuggestionSupport", "suggest_column_reorder"),
    TableConstraintChangeSuggestion: (
        "TableConstraintChangeSuggestionSupport",
        "suggest_table_constraint_change",
    ),
    TableIndexChangeSuggestion: ("TableIndexChangeSuggestionSupport", "suggest_table_index_change"),
    PartitionSchemeChangeSuggestion: (
        "PartitionSchemeChangeSuggestionSupport",
        "suggest_partition_scheme_change",
    ),
}


@dataclass(frozen=True)
class ResolvedSuggestion:
    """One frozen point's tri-state answer from a dialect.

    ``state`` is one of:

    * ``"actions"`` -- ``operations`` holds the backend's expression chain;
    * ``"unsupported"`` -- the backend answered ``False`` (it cannot address
      the change automatically);
    * ``"no-answer"`` -- the backend answered ``None`` (no action required);
    * ``"missing-protocol"`` -- the dialect does not implement the protocol.

    ``protocol`` names the protocol class, so a refusal can point at it.
    """

    point: SuggestionPoint
    state: str
    protocol: str
    operations: Tuple[Any, ...] = ()

    @property
    def is_actionable(self) -> bool:
        return self.state == "actions"

    def operations_or_none(self) -> Optional[Tuple[Any, ...]]:
        """The chain only for ``"actions"``; ``None`` for every other state."""
        return self.operations if self.state == "actions" else None


@dataclass
class SuggestionResolution:
    """Aggregate outcome of :func:`resolve_suggestions`.

    ``statements`` are the expressions appended to the plan's executable
    statement list. ``entries`` records every considered point in plan order,
    so a caller can report exactly which points remain unresolved and why.
    """

    entries: List[ResolvedSuggestion] = field(default_factory=list)
    statements: List[Any] = field(default_factory=list)

    @property
    def resolved(self) -> List[ResolvedSuggestion]:
        return [entry for entry in self.entries if entry.state == "actions"]

    @property
    def unsupported(self) -> List[ResolvedSuggestion]:
        return [entry for entry in self.entries if entry.state == "unsupported"]

    @property
    def no_answer(self) -> List[ResolvedSuggestion]:
        return [entry for entry in self.entries if entry.state == "no-answer"]

    @property
    def missing(self) -> List[ResolvedSuggestion]:
        return [entry for entry in self.entries if entry.state == "missing-protocol"]

    @property
    def unresolved(self) -> List[ResolvedSuggestion]:
        return [entry for entry in self.entries if entry.state != "actions"]

    @property
    def is_complete(self) -> bool:
        """True when no considered point was left unresolved."""
        return not self.unresolved


def _protocol_for(point: Any) -> Optional[Tuple[str, str]]:
    for point_cls, names in _CHANGE_SUGGESTION_PROTOCOLS.items():
        if isinstance(point, point_cls):
            return names
    return None


def _check_single_action(expression: Any, protocol: str, label: str) -> None:
    """Enforce 1 expression -> 1 statement.

    A statement carrying several actions would silently bundle work the
    contract keeps separate. Refuse it and name the protocol that produced it.
    """
    actions = getattr(expression, "actions", None)
    if isinstance(actions, (list, tuple)) and len(actions) > 1:
        raise ValueError(
            f"{protocol} returned a multi-action statement for '{label}': "
            "one expression must map to exactly one action; return one "
            "single-action statement per expression instead."
        )


def resolve_point(point: SuggestionPoint, dialect: Any) -> ResolvedSuggestion:
    """Consume one frozen change point against *dialect*, keeping tri-state.

    This is the A-side consumer of the four ``suggest_*`` protocols. The
    returned chain is exactly what the backend handed back -- no SQL is
    rendered and no expression type is constructed here. ``False`` is reported
    as ``"unsupported"`` and ``None`` as ``"no-answer"``; neither is collapsed
    into the other, and a missing protocol is reported as ``"missing-protocol"``.
    """
    from ..backend.suggestion import protocols as suggestion_protocols

    names = _protocol_for(point)
    if names is None:
        raise ValueError(f"unsupported suggestion point type: {type(point).__name__}")
    protocol_name, method_name = names
    label = getattr(point, "label", "")
    protocol = getattr(suggestion_protocols, protocol_name)
    if not isinstance(dialect, protocol):
        return ResolvedSuggestion(point, "missing-protocol", protocol_name)

    answer = getattr(dialect, method_name)(point)
    if answer is False:
        operations: Any = False
    elif answer is None:
        operations = None
    else:
        operations = getattr(answer, "operations", None)

    if isinstance(operations, (list, tuple)):
        chain = tuple(operations)
        for expression in chain:
            _check_single_action(expression, protocol_name, label)
        return ResolvedSuggestion(point, "actions", protocol_name, chain)
    if operations is False:
        return ResolvedSuggestion(point, "unsupported", protocol_name)
    return ResolvedSuggestion(point, "no-answer", protocol_name)


def resolve_suggestions(plan: ChangePlan, dialect: Any) -> SuggestionResolution:
    """Resolve every frozen point in *plan* against *dialect*.

    An explicit, caller-invoked step: :func:`plan_changes` is unchanged and
    still emits only single-action statements plus frozen points. Actionable
    chains are appended to ``plan.statements`` (the list
    ``MigrationContext.apply`` executes); the returned report records every
    point's state, so ``False`` (unsupported), ``None`` (no-answer) and a
    missing protocol are never silently dropped.

    Resolution is one-shot per point: a second call does not append the same
    statements again. Legacy bare-label entries carry no decision data and are
    skipped.
    """
    result = SuggestionResolution()
    seen = plan._resolved_point_ids

    point_types = (
        ColumnReorderSuggestion,
        TableConstraintChangeSuggestion,
        TableIndexChangeSuggestion,
        PartitionSchemeChangeSuggestion,
    )
    for point in plan.suggestion_points:
        if not isinstance(point, point_types):
            continue
        if id(point) in seen:
            continue
        entry = resolve_point(point, dialect)
        seen.add(id(point))
        result.entries.append(entry)
        if entry.is_actionable:
            result.statements.extend(entry.operations)
            plan.statements.extend(entry.operations)
    return result
