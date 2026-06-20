# src/rhosocial/activerecord/backend/schema/differ.py
"""Schema comparison — diff data classes and generic differ (ABC)."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..introspection.types import TableInfo, ColumnInfo, IndexInfo, ForeignKeyInfo


# ---------------------------------------------------------------------------
# Diff data classes
# ---------------------------------------------------------------------------


@dataclass
class ColumnDiff:
    """Difference for a single column."""
    column_name: str
    old: Optional["ColumnInfo"]   # None = column added
    new: Optional["ColumnInfo"]   # None = column removed

    @property
    def is_added(self) -> bool:
        return self.old is None

    @property
    def is_removed(self) -> bool:
        return self.new is None

    @property
    def is_modified(self) -> bool:
        return self.old is not None and self.new is not None


@dataclass
class TableDiff:
    """Difference for a single table."""
    table_name: str
    old: Optional["TableInfo"]     # None = table added
    new: Optional["TableInfo"]     # None = table removed
    column_diffs: List[ColumnDiff] = field(default_factory=list)
    added_indexes: List["IndexInfo"] = field(default_factory=list)
    removed_indexes: List["IndexInfo"] = field(default_factory=list)
    added_foreign_keys: List["ForeignKeyInfo"] = field(default_factory=list)
    removed_foreign_keys: List["ForeignKeyInfo"] = field(default_factory=list)

    @property
    def is_added(self) -> bool:
        return self.old is None

    @property
    def is_removed(self) -> bool:
        return self.new is None

    @property
    def is_modified(self) -> bool:
        return self.old is not None and self.new is not None

    @property
    def has_changes(self) -> bool:
        return (
            self.is_added or self.is_removed
            or bool(self.column_diffs)
            or bool(self.added_indexes) or bool(self.removed_indexes)
            or bool(self.added_foreign_keys) or bool(self.removed_foreign_keys)
        )


@dataclass
class SchemaDiff:
    """Result of comparing two ``SchemaSnapshot`` instances."""
    dialect_class: str
    table_diffs: Dict[str, TableDiff] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return all(not td.has_changes for td in self.table_diffs.values())

    @property
    def added_tables(self) -> List[str]:
        return [n for n, td in self.table_diffs.items() if td.is_added]

    @property
    def removed_tables(self) -> List[str]:
        return [n for n, td in self.table_diffs.items() if td.is_removed]

    @property
    def modified_tables(self) -> List[str]:
        return [n for n, td in self.table_diffs.items() if td.is_modified and td.has_changes]


# ---------------------------------------------------------------------------
# Differ base class
# ---------------------------------------------------------------------------


class SchemaDiffer(ABC):
    """Abstract base for schema comparison.

    Subclass and override ``_columns_equivalent`` (and optionally
    ``_diff_table``) to implement backend-specific comparison rules.
    """

    def compare(self, old: "SchemaSnapshot", new: "SchemaSnapshot") -> SchemaDiff:
        from .snapshot import SchemaSnapshot

        if old.dialect_class != new.dialect_class:
            raise ValueError(
                f"Cannot compare snapshots from different dialects: "
                f"{old.dialect_class!r} vs {new.dialect_class!r}"
            )
        diff = SchemaDiff(dialect_class=old.dialect_class)
        old_tables = set(old.tables)
        new_tables = set(new.tables)
        for name in old_tables - new_tables:
            diff.table_diffs[name] = TableDiff(table_name=name, old=old.tables[name], new=None)
        for name in new_tables - old_tables:
            diff.table_diffs[name] = TableDiff(table_name=name, old=None, new=new.tables[name])
        for name in old_tables & new_tables:
            td = self._diff_table(name, old.tables[name], new.tables[name])
            if td.has_changes:
                diff.table_diffs[name] = td
        return diff

    def _diff_table(self, name: str, old_tbl, new_tbl) -> TableDiff:
        td = TableDiff(table_name=name, old=old_tbl, new=new_tbl)

        old_cols = {c.name: c for c in old_tbl.columns}
        new_cols = {c.name: c for c in new_tbl.columns}
        for col_name in set(old_cols) - set(new_cols):
            td.column_diffs.append(ColumnDiff(col_name, old_cols[col_name], None))
        for col_name in set(new_cols) - set(old_cols):
            td.column_diffs.append(ColumnDiff(col_name, None, new_cols[col_name]))
        for col_name in set(old_cols) & set(new_cols):
            if not self._columns_equivalent(old_cols[col_name], new_cols[col_name]):
                td.column_diffs.append(ColumnDiff(col_name, old_cols[col_name], new_cols[col_name]))

        old_idx = {i.name: i for i in old_tbl.indexes}
        new_idx = {i.name: i for i in new_tbl.indexes}
        td.added_indexes = [new_idx[n] for n in set(new_idx) - set(old_idx)]
        td.removed_indexes = [old_idx[n] for n in set(old_idx) - set(new_idx)]
        for idx_name in set(old_idx) & set(new_idx):
            if not self._indexes_equivalent(old_idx[idx_name], new_idx[idx_name]):
                td.removed_indexes.append(old_idx[idx_name])
                td.added_indexes.append(new_idx[idx_name])

        old_fk = {f.name: f for f in old_tbl.foreign_keys}
        new_fk = {f.name: f for f in new_tbl.foreign_keys}
        td.added_foreign_keys = [new_fk[n] for n in set(new_fk) - set(old_fk)]
        td.removed_foreign_keys = [old_fk[n] for n in set(old_fk) - set(new_fk)]
        for fk_name in set(old_fk) & set(new_fk):
            if not self._fk_equivalent(old_fk[fk_name], new_fk[fk_name]):
                td.removed_foreign_keys.append(old_fk[fk_name])
                td.added_foreign_keys.append(new_fk[fk_name])

        return td

    def _columns_equivalent(self, old_col, new_col) -> bool:
        """Column equivalence: type + nullability + default value.

        Override in subclasses to add backend-specific rules
        (e.g. ``ordinal_position`` check for MySQL).
        """
        old_dt, new_dt = old_col.parsed_data_type, new_col.parsed_data_type
        if old_dt is not None and new_dt is not None:
            if not old_dt.is_equivalent(new_dt):
                return False
        else:
            if (old_col.data_type or "").upper().split() != (new_col.data_type or "").upper().split():
                return False
        if old_col.nullable != new_col.nullable:
            return False
        if old_col.default_value != new_col.default_value:
            return False
        return True

    def _indexes_equivalent(self, old_idx, new_idx) -> bool:
        """Index equivalence: unique/primary flag + index_type + column list."""
        if old_idx.is_unique != new_idx.is_unique:
            return False
        if old_idx.is_primary != new_idx.is_primary:
            return False
        if old_idx.index_type != new_idx.index_type:
            return False
        old_cols = [(c.name, c.is_descending) for c in old_idx.columns]
        new_cols = [(c.name, c.is_descending) for c in new_idx.columns]
        return old_cols == new_cols

    def _fk_equivalent(self, old_fk, new_fk) -> bool:
        """Foreign key equivalence: columns + referenced table/columns + actions."""
        return (
            old_fk.columns == new_fk.columns
            and old_fk.referenced_table == new_fk.referenced_table
            and old_fk.referenced_columns == new_fk.referenced_columns
            and old_fk.on_update == new_fk.on_update
            and old_fk.on_delete == new_fk.on_delete
        )
