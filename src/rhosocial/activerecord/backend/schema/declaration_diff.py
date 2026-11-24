# src/rhosocial/activerecord/backend/schema/declaration_diff.py
"""Direct comparison of two ActiveRecord model declarations.

This is the planner-facing diff path: it reads the declaration surface already
exposed by :class:`ModelDDLDeclaration` field-by-field, table-by-table, and
produces the same :class:`SchemaDiff` data classes as the introspection path.
No conversion through ``IntrospectionColumnInfo`` is involved — the model's
declarations are the source of truth, and nothing is lost in translation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence, TYPE_CHECKING

from .differ import (
    ColumnChangeKind,
    ColumnDiff,
    SchemaDiff,
    TableDiff,
)

if TYPE_CHECKING:  # pragma: no cover
    from ...base.ddl import ModelDDLDeclaration


@dataclass
class FieldDeclaration:
    """The comparable declaration of one model field.

    A lightweight, dialect-free snapshot of what the model declares for a
    field. Held in ``ColumnDiff.old``/``new`` so a diff result is self-contained
    and a planner can read it without the model still being alive. Values come
    straight from ``ModelDDLDeclaration`` accessors.
    """

    name: str
    python_type: Any = None
    declared_type: Any = None
    constraints: Sequence[Any] = field(default_factory=tuple)
    attributes: Sequence[Any] = field(default_factory=tuple)
    comment: Optional[str] = None
    has_identity: bool = False
    generated: Any = None
    index_names: Sequence[str] = field(default_factory=tuple)

    def signature(self) -> tuple:
        """A hashable, comparable signature of the declared facts."""
        return (
            self.python_type,
            _freeze(self.declared_type),
            tuple(_freeze(c) for c in self.constraints),
            tuple(_freeze(a) for a in self.attributes),
            self.comment,
            self.has_identity,
            _freeze(self.generated),
            tuple(self.index_names),
        )


@dataclass
class TableDeclaration:
    """The comparable declaration of one model (one table)."""

    table_name: str
    fields: Dict[str, FieldDeclaration] = field(default_factory=dict)
    field_order: Sequence[str] = field(default_factory=tuple)
    table_constraints: Sequence[Any] = field(default_factory=tuple)
    table_indexes: Sequence[Any] = field(default_factory=tuple)
    table_options: Sequence[Any] = field(default_factory=tuple)
    partition: Any = None


def _freeze(value: Any) -> Any:
    """Turn a declaration value into a comparable/hashable form.

    ``DataType`` and marker value objects are immutable and compare by value;
    expression nodes are compared by their serialised parameters via
    ``get_params()`` when available, else by ``repr``. This keeps the diff
    deterministic without rendering SQL (which would need a dialect).
    """
    if value is None or isinstance(value, (str, int, float, bool, bytes, tuple)):
        return value
    getter = getattr(value, "get_params", None)
    if callable(getter):
        try:
            return ("params", _freeze(getter()))
        except Exception:  # pragma: no cover - a broken node must not abort a diff
            pass
    if isinstance(value, (list, set, frozenset)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((str(k), _freeze(v)) for k, v in value.items()))
    return ("repr", repr(value))


def field_declaration(source: "ModelDDLDeclaration", field_name: str, dialect: Any = None) -> FieldDeclaration:
    """Read one field's declaration surface from a model into a comparable value."""
    from ...base.derivation import _has_declared_identity

    return FieldDeclaration(
        name=source.column_name(field_name),
        python_type=source.field_python_type(field_name),
        declared_type=source.column_data_type(field_name),
        constraints=tuple(source.column_constraints(field_name)),
        attributes=tuple(source.column_attributes(field_name)),
        comment=source.column_comment(field_name),
        has_identity=_has_declared_identity(source, field_name),
        generated=source.generated_column(field_name),
        index_names=tuple(idx.name for idx in source.column_indexes(field_name)),
    )


def table_declaration(source: "ModelDDLDeclaration", dialect: Any = None) -> TableDeclaration:
    """Read a whole model's declaration surface into a comparable value."""
    names = tuple(source.ddl_field_names())
    return TableDeclaration(
        table_name=source.table_name(),
        fields={n: field_declaration(source, n, dialect) for n in names},
        field_order=names,
        table_constraints=tuple(source.table_constraints()),
        table_indexes=tuple(source.table_indexes()),
        table_options=tuple(source.table_options() or ()),
        partition=source.table_partition(),
    )


class DeclarationDiffer:
    """Compare two ActiveRecord model declarations field-by-field, table-by-table."""

    def compare(
        self,
        old_source: "ModelDDLDeclaration",
        new_source: "ModelDDLDeclaration",
        dialect: Any = None,
    ) -> SchemaDiff:
        old = table_declaration(old_source, dialect)
        new = table_declaration(new_source, dialect)
        diff = SchemaDiff(dialect_class=getattr(dialect, "__class__", type(None)).__name__)

        if old.table_name != new.table_name:
            # Different table names: report as remove + add rather than guess a rename.
            diff.table_diffs[old.table_name] = TableDiff(
                table_name=old.table_name, old=old, new=None
            )
            diff.table_diffs[new.table_name] = TableDiff(
                table_name=new.table_name, old=None, new=new
            )
            return diff

        td = TableDiff(table_name=new.table_name, old=old, new=new)
        for name in set(old.fields) - set(new.fields):
            td.column_diffs.append(
                ColumnDiff(name, old.fields[name], None, kind=ColumnChangeKind.DROP)
            )
        for name in set(new.fields) - set(old.fields):
            td.column_diffs.append(
                ColumnDiff(name, None, new.fields[name], kind=ColumnChangeKind.ADD)
            )
        for name in set(old.fields) & set(new.fields):
            of, nf = old.fields[name], new.fields[name]
            if of.signature() != nf.signature():
                td.column_diffs.append(
                    ColumnDiff(name, of, nf, kind=ColumnChangeKind.MODIFY)
                )

        common_order = [n for n in new.field_order if n in old.fields]
        old_order = [n for n in old.field_order if n in new.fields]
        td.reordered_columns = [
            n for n in common_order if common_order.index(n) != old_order.index(n)
        ]
        td.table_options_changed = _freeze(old.table_options) != _freeze(new.table_options)
        td.comment_changed = any(
            c.comment != n.comment for c, n in (
                (old.fields[k], new.fields[k]) for k in set(old.fields) & set(new.fields)
            )
        )

        if td.has_changes:
            diff.table_diffs[new.table_name] = td
        return diff
