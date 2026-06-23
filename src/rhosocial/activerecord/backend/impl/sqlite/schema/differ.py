# src/rhosocial/activerecord/backend/impl/sqlite/schema/differ.py
"""SQLite schema differ — FK matching by content instead of name."""

from typing import Dict, List, Optional

from ....schema.differ import ColumnDiff, SchemaDiffer, TableDiff


class SQLiteSchemaDiffer(SchemaDiffer):
    """SQLite schema differ.

    SQLite has no column-order semantics, so the default
    ``_columns_equivalent`` is sufficient — only type, nullability,
    and default value are compared.

    FK matching uses content-based comparison (columns + referenced_table
    + referenced_columns) instead of FK names, because SQLite generates
    FK names from PRAGMA ids which are unstable across schema roundtrips.
    """

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

        # SQLite: match FKs by content (columns + ref_table + ref_columns) instead of
        # by pragma-based name, which is unstable across schema roundtrips.
        old_fk = self._fk_content_map(old_tbl.foreign_keys)
        new_fk = self._fk_content_map(new_tbl.foreign_keys)
        for key in set(old_fk) - set(new_fk):
            td.removed_foreign_keys.append(old_fk[key])
        for key in set(new_fk) - set(old_fk):
            td.added_foreign_keys.append(new_fk[key])
        for key in set(old_fk) & set(new_fk):
            if not self._fk_equivalent(old_fk[key], new_fk[key]):
                td.removed_foreign_keys.append(old_fk[key])
                td.added_foreign_keys.append(new_fk[key])

        return td

    @staticmethod
    def _fk_content_key(fk) -> tuple:
        return (
            tuple(fk.columns),
            fk.referenced_table,
            tuple(fk.referenced_columns),
        )

    def _fk_content_map(self, fk_list: List) -> Dict[tuple, object]:
        return {self._fk_content_key(fk): fk for fk in fk_list}
