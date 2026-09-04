# src/rhosocial/activerecord/backend/dialect/mixins/ddl_diff.py
"""Generic CREATE TABLE expression diff (``CreateTableExpressionDiffSupport``).

Hosted on the dialect because equivalence rules and rebuild thresholds are
backend policy, while the diff operates purely on expression structures.
The generic implementation is deliberately strict; see the class docstring
for the full strictness contract.
"""

from typing import Any, List, Optional, Tuple

from ...expression.statements.ddl_alter import (
    AddColumn,
    AddIndex,
    AddTableConstraint,
    AlterColumn,
    AlterTableAction,
    AlterTableExpression,
    ColumnAlterOperation,
    DropColumn,
    DropIndex,
    DropTableConstraint,
    RenameTable,
)
from ...expression.statements.ddl_diff import DiffPlan, RebuildPlan
from ...expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnDefinition,
    CreateTableExpression,
    DropTableExpression,
    TableConstraintType,
)


class CreateTableExpressionDiffMixin:
    """Generic, strict structural diff between two CreateTableExpression.

    Satisfies the ``CreateTableExpressionDiffSupport`` protocol via
    :meth:`diff_create_table`. Composed into ``SQLDialectBase`` so every
    dialect provides a working default; backends override the hooks below.

    Strictness contract of the default implementation:

    - **Column type**: exact ``DataType`` equality (dataclass ``__eq__``);
      no alias tolerance. Backends relax via :meth:`_data_types_equal`.
    - **In-place column type change**: not portable SQL →
      :meth:`_supports_alter_column_type` defaults to False, so type changes
      route to ``RebuildPlan``. Backends with native support (MySQL
      ``MODIFY COLUMN``) override the flag *and*
      :meth:`alter_column_type_action`.
    - **Column property changes** (SET/DROP DEFAULT, SET/DROP NOT NULL):
      degrade to ``AlterColumn`` actions when
      :meth:`_supports_alter_column_properties` (default True); otherwise
      rebuild. SQLite overrides to False (no ``ALTER COLUMN`` at all).
    - **Column renames**: NOT detected — rendered as drop + add. Rename
      detection requires user intent (future enhancement).
    - **Index changes**: add/drop/redfine actions when
      :meth:`_supports_alter_table_index_actions` (default True); else
      rebuild (the recreated table carries the new indexes). SQLite
      overrides to False (``ALTER TABLE ADD INDEX`` unsupported).
    - **Table constraints**: named non-PK constraints → add/drop actions;
      PK changes or unnamed constraint changes → rebuild (unnamed
      constraints cannot be addressed by ``DROP CONSTRAINT``).
    - **Structural fields** (temporary, inherits, tablespace, storage
      options, partition, table options) → rebuild.
    - **Cross-dialect / cross-table**: ``ValueError``.
    """

    # ------------------------------------------------------------------
    # Public entry point (satisfies CreateTableExpressionDiffSupport)
    # ------------------------------------------------------------------
    def diff_create_table(self, old: CreateTableExpression, new: CreateTableExpression) -> DiffPlan:
        """Compute the diff between two CREATE TABLE expressions."""
        self._validate_pair(old, new)
        notes: List[str] = []

        if self._tables_equal(old, new):
            return DiffPlan()

        if self._structural_changes_present(old, new):
            return DiffPlan(
                rebuild=self._build_rebuild_plan(old, new, reason="structural option change"),
            )

        constraint_drops, constraint_adds, constraint_rebuild = self._diff_table_constraints(old, new)
        if constraint_rebuild is not None:
            return DiffPlan(
                rebuild=constraint_rebuild,
                notes=notes,
            )

        col_actions, col_rebuild = self._diff_columns(old, new)
        if col_rebuild is not None:
            return DiffPlan(rebuild=col_rebuild, notes=notes)

        if self._supports_alter_table_index_actions():
            index_actions, index_notes = self._diff_indexes(old, new)
            notes.extend(index_notes)
        else:
            index_actions = []
            if old.indexes != new.indexes:
                return DiffPlan(
                    rebuild=self._build_rebuild_plan(old, new, reason="index change"),
                    notes=notes,
                )

        actions: List[AlterTableAction] = [
            *constraint_drops,
            *col_actions,
            *constraint_adds,
            *index_actions,
        ]
        if not actions:
            return DiffPlan(notes=notes)
        return DiffPlan(
            alters=[AlterTableExpression(self, table=old.table_name, actions=actions)],
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate_pair(self, old: CreateTableExpression, new: CreateTableExpression) -> None:
        if old.dialect.name != new.dialect.name:
            raise ValueError(
                f"Cannot diff expressions from different dialects: "
                f"{old.dialect.name!r} vs {new.dialect.name!r}"
            )
        if old.table_name != new.table_name:
            raise ValueError(
                f"Cannot diff expressions for different tables: "
                f"{old.table_name!r} vs {new.table_name!r}. "
                f"Table renames must be issued explicitly via RenameTable."
            )

    # ------------------------------------------------------------------
    # Equality hooks (override points for backends)
    # ------------------------------------------------------------------
    def _tables_equal(self, old: CreateTableExpression, new: CreateTableExpression) -> bool:
        """Whether the two definitions are semantically identical (override to relax)."""
        if len(old.columns) != len(new.columns):
            return False
        if not all(self._column_equal(o, n) for o, n in zip(old.columns, new.columns)):
            return False
        if {i.name: i for i in old.indexes} != {i.name: i for i in new.indexes}:
            return False
        if sorted(old.table_constraints, key=self._constraint_sort_key) != sorted(
            new.table_constraints, key=self._constraint_sort_key
        ):
            return False
        if self._structural_changes_present(old, new):
            return False
        return True

    def _data_types_equal(self, old_dt: Any, new_dt: Any) -> bool:
        """Type equality hook (override to tolerate aliases, e.g. INT ≡ INTEGER)."""
        return bool(old_dt == new_dt)

    def _column_equal(self, old_col: ColumnDefinition, new_col: ColumnDefinition) -> bool:
        if old_col.name != new_col.name:
            return False
        if not self._data_types_equal(old_col.data_type, new_col.data_type):
            return False
        if old_col.comment != new_col.comment:
            return False
        old_cs = sorted(old_col.constraints, key=lambda c: (c.constraint_type.value, c.name or ""))
        new_cs = sorted(new_col.constraints, key=lambda c: (c.constraint_type.value, c.name or ""))
        if len(old_cs) != len(new_cs):
            return False
        return all(o == n for o, n in zip(old_cs, new_cs))

    @staticmethod
    def _constraint_sort_key(c) -> Tuple:
        return (c.constraint_type.value, c.name or "", tuple(c.columns or ()))

    # ------------------------------------------------------------------
    # Column diffing
    # ------------------------------------------------------------------
    def _diff_columns(
        self, old: CreateTableExpression, new: CreateTableExpression
    ) -> Tuple[List[AlterTableAction], Optional[RebuildPlan]]:
        """Diff column lists → (actions, rebuild_or_None)."""
        old_by_name = {c.name: c for c in old.columns}
        new_by_name = {c.name: c for c in new.columns}
        actions: List[AlterTableAction] = []

        for col in new.columns:
            old_col = old_by_name.get(col.name)
            if old_col is None:
                actions.append(AddColumn(self, column=col))
                continue
            if self._column_equal(old_col, col):
                continue
            if not self._data_types_equal(old_col.data_type, col.data_type):
                if not self._supports_alter_column_type():
                    return [], self._build_rebuild_plan(
                        old, new,
                        reason=f"column {col.name!r}: type change not supported in-place by {self.name}",
                    )
                actions.append(self.alter_column_type_action(old_col, col))
                continue
            if not self._supports_alter_column_properties():
                return [], self._build_rebuild_plan(
                    old, new,
                    reason=f"column {col.name!r}: property change not supported in-place by {self.name}",
                )
            prop_actions, residual = self._diff_column_properties(old_col, col)
            if residual:
                return [], self._build_rebuild_plan(
                    old, new,
                    reason=f"column {col.name!r}: constraint set change not expressible in-place",
                )
            actions.extend(prop_actions)

        for col in old.columns:
            if col.name not in new_by_name:
                actions.append(DropColumn(self, column_name=col.name))

        return actions, None

    def _diff_column_properties(
        self, old_col: ColumnDefinition, new_col: ColumnDefinition
    ) -> Tuple[List[AlterTableAction], bool]:
        """Property-only changes for a common column → (actions, residual_difference).

        ``residual`` is True when the constraint sets differ beyond
        default/nullability — i.e. the change cannot be explained by the
        SET/DROP operations this method emits.
        """
        actions: List[AlterTableAction] = []

        old_default = self._find_default(old_col)
        new_default = self._find_default(new_col)
        if not self._defaults_equal(old_default, new_default):
            if new_default is None:
                actions.append(AlterColumn(self, new_col.name, ColumnAlterOperation.DROP_DEFAULT))
            else:
                actions.append(
                    AlterColumn(
                        self, new_col.name, ColumnAlterOperation.SET_DEFAULT,
                        new_value=new_default.default_value,
                    )
                )

        old_nullable, new_nullable = self._nullability(old_col), self._nullability(new_col)
        if old_nullable != new_nullable:
            if new_nullable:
                actions.append(AlterColumn(self, new_col.name, ColumnAlterOperation.DROP_NOT_NULL))
            else:
                actions.append(AlterColumn(self, new_col.name, ColumnAlterOperation.SET_NOT_NULL))

        residual = not self._constraints_residue_equal(old_col.constraints, new_col.constraints)
        return actions, residual

    def _defaults_equal(self, old_c: Optional[ColumnConstraint], new_c: Optional[ColumnConstraint]) -> bool:
        old_v = old_c.default_value if old_c is not None else None
        new_v = new_c.default_value if new_c is not None else None
        return old_v == new_v

    @staticmethod
    def _find_default(col: ColumnDefinition) -> Optional[ColumnConstraint]:
        for c in col.constraints:
            if c.constraint_type.value == "DEFAULT":
                return c
        return None

    @staticmethod
    def _nullability(col: ColumnDefinition) -> bool:
        for c in col.constraints:
            if c.constraint_type.value in ("NOT NULL", "PRIMARY KEY"):
                return False
            if c.constraint_type.value == "NULL":
                return True
        return True

    def _constraints_residue_equal(self, old_cs: List[ColumnConstraint], new_cs: List[ColumnConstraint]) -> bool:
        """Whether constraint multisets match, ignoring DEFAULT and NULL entries
        (those are handled by the SET/DROP property operations)."""
        def sig(cs: List[ColumnConstraint]) -> List[Tuple]:
            kept = [
                self._constraint_signature(c)
                for c in cs
                if c.constraint_type.value not in ("DEFAULT", "NULL", "NOT NULL")
            ]
            return sorted(kept, key=repr)
        return sig(old_cs) == sig(new_cs)

    @staticmethod
    def _constraint_signature(c) -> Tuple:
        """Structural signature shared by ColumnConstraint and TableConstraint.

        ``check_condition`` predicates may lack value equality, so they are
        compared via ``repr``.
        """
        fk = getattr(c, "foreign_key_reference", None)
        if fk is None and getattr(c, "foreign_key_table", None) is not None:
            fk = (c.foreign_key_table, tuple(c.foreign_key_columns or ()))
        return (
            c.constraint_type.value,
            getattr(c, "name", None),
            repr(getattr(c, "columns", None)),
            repr(getattr(c, "check_condition", None)),
            repr(fk),
            getattr(c, "is_auto_increment", False),
            getattr(c, "on_delete", None),
            getattr(c, "on_update", None),
            getattr(c, "deferrable", None),
            getattr(c, "character_set", None),
            getattr(c, "collation", None),
            repr(sorted((getattr(c, "dialect_options", None) or {}).items())),
        )

    # ------------------------------------------------------------------
    # Index diffing
    # ------------------------------------------------------------------
    def _diff_indexes(
        self, old: CreateTableExpression, new: CreateTableExpression
    ) -> Tuple[List[AlterTableAction], List[str]]:
        old_by_name = {i.name: i for i in old.indexes}
        new_by_name = {i.name: i for i in new.indexes}
        actions: List[AlterTableAction] = []
        notes: List[str] = []
        for name, idx in new_by_name.items():
            if name not in old_by_name:
                actions.append(AddIndex(self, index=idx))
            elif old_by_name[name] != idx:
                actions.append(DropIndex(self, index=name))
                actions.append(AddIndex(self, index=idx))
                notes.append(f"index {name!r} redefined")
        for name in old_by_name:
            if name not in new_by_name:
                actions.append(DropIndex(self, index=name))
        return actions, notes

    # ------------------------------------------------------------------
    # Table constraint diffing
    # ------------------------------------------------------------------
    def _diff_table_constraints(
        self, old: CreateTableExpression, new: CreateTableExpression
    ) -> Tuple[List[AlterTableAction], List[AlterTableAction], Optional[RebuildPlan]]:
        """Diff table-level constraints → (drops, adds, rebuild_or_None).

        PK changes and unnamed constraint changes always rebuild: a primary
        key change is structural on every backend, and unnamed constraints
        cannot be addressed by ``DROP CONSTRAINT <name>``.
        """
        old_list, new_list = old.table_constraints, new.table_constraints
        pk_changed = self._pk_signature(old_list) != self._pk_signature(new_list)
        if pk_changed:
            return [], [], self._build_rebuild_plan(old, new, reason="primary key change")

        old_unnamed = sorted(
            (self._constraint_signature(c) for c in old_list if not c.name), key=repr
        )
        new_unnamed = sorted(
            (self._constraint_signature(c) for c in new_list if not c.name), key=repr
        )
        if old_unnamed != new_unnamed:
            return [], [], self._build_rebuild_plan(old, new, reason="unnamed table constraint change")

        old_named = {c.name: c for c in old_list if c.name}
        new_named = {c.name: c for c in new_list if c.name}
        drops: List[AlterTableAction] = []
        adds: List[AlterTableAction] = []
        for name, c in new_named.items():
            if name not in old_named:
                adds.append(AddTableConstraint(self, constraint=c))
            elif old_named[name] != c:
                drops.append(DropTableConstraint(self, constraint_name=name))
                adds.append(AddTableConstraint(self, constraint=c))
        for name in old_named:
            if name not in new_named:
                drops.append(DropTableConstraint(self, constraint_name=name))
        return drops, adds, None

    @staticmethod
    def _pk_signature(constraints) -> List[Tuple]:
        return sorted(
            (
                c.name,
                tuple(c.columns or ()),
                repr(sorted((c.dialect_options or {}).items())),
            )
            for c in constraints
            if c.constraint_type == TableConstraintType.PRIMARY_KEY
        )

    # ------------------------------------------------------------------
    # Structural rebuild
    # ------------------------------------------------------------------
    def _structural_changes_present(self, old: CreateTableExpression, new: CreateTableExpression) -> bool:
        return (
            old.temporary != new.temporary
            or old.inherits != new.inherits
            or old.tablespace != new.tablespace
            or old.storage_options != new.storage_options
            or not self._partition_equivalent(old.partition, new.partition)
            or not self._table_options_equal(old.table_options, new.table_options)
        )

    def _partition_equivalent(self, old_p, new_p) -> bool:
        """Partition equivalence: structural identity, guarded SQL fallback.

        No backend can ALTER a partition key onto an existing table, so any
        partition difference forces a rebuild. When clause rendering fails
        (e.g. a dialect without partition support), treat as different —
        safe and explicit.
        """
        if (old_p is None) != (new_p is None):
            return False
        if old_p is None:
            return True
        if old_p is new_p:
            return True
        try:
            return old_p.to_sql() == new_p.to_sql()
        except Exception:
            return False

    def _table_options_equal(self, old_opts, new_opts) -> bool:
        if old_opts is None and new_opts is None:
            return True
        if old_opts is None or new_opts is None:
            return False
        return old_opts == new_opts

    def _build_rebuild_plan(
        self,
        old: CreateTableExpression,
        new: CreateTableExpression,
        reason: str = "",
    ) -> RebuildPlan:
        """Assemble a rebuild plan: create temp → (caller copies data) → drop old → rename."""
        old_names = {c.name for c in old.columns}
        copy_columns = [c.name for c in new.columns if c.name in old_names]
        temp = f"{new.table_name}__rebuild__"
        return RebuildPlan(
            create=self._clone_create_table(new, table_name=temp),
            drop_old=DropTableExpression(self, old.table_name),
            rename=AlterTableExpression(
                self,
                table=temp,
                actions=[RenameTable(self, temp, new.table_name)],
            ),
            temp_table_name=temp,
            copy_columns=copy_columns,
            reason=reason,
        )

    def _clone_create_table(
        self, expr: CreateTableExpression, table_name: Optional[str] = None
    ) -> CreateTableExpression:
        """Clone a CREATE TABLE expression, optionally retargeting the table name."""
        return CreateTableExpression(
            dialect=self,
            table=table_name or expr.table_name,
            columns=list(expr.columns),
            indexes=list(expr.indexes),
            table_constraints=list(expr.table_constraints),
            table_options=expr.table_options,
            temporary=expr.temporary,
            if_not_exists=False,
            inherits=list(expr.inherits),
            tablespace=expr.tablespace,
            storage_options=dict(expr.storage_options),
            as_query=expr.as_query,
            partition=expr.partition,
            dialect_options=dict(expr.dialect_options),
        )

    # ------------------------------------------------------------------
    # Capability hooks (override points for backends)
    # ------------------------------------------------------------------
    def _supports_alter_column_type(self) -> bool:
        """Whether ALTER TABLE can change a column type in place.

        Portable SQL cannot; MySQL/MariaDB (``MODIFY COLUMN``) and a few
        others override this to True together with
        :meth:`alter_column_type_action`. SQLite has no ``ALTER COLUMN``
        and keeps the default (type changes → rebuild).
        """
        return False

    def alter_column_type_action(
        self, old_col: ColumnDefinition, new_col: ColumnDefinition
    ) -> AlterTableAction:
        """Build the in-place action for a column type change.

        Only called when :meth:`_supports_alter_column_type` is True;
        the default raises because the generic mixin has no portable
        type-change action.
        """
        raise NotImplementedError(
            f"{type(self).__name__} declares in-place column type change support "
            f"but does not implement alter_column_type_action()"
        )

    def _supports_alter_column_properties(self) -> bool:
        """Whether SET/DROP DEFAULT and SET/DROP NOT NULL work via ALTER TABLE.

        True for most standard backends; SQLite overrides to False (no
        ``ALTER COLUMN`` at all — property changes → rebuild).
        """
        return True

    def _supports_alter_table_index_actions(self) -> bool:
        """Whether ALTER TABLE ADD/DROP INDEX actions are renderable.

        True for MySQL/MariaDB; SQLite overrides to False (``ALTER TABLE
        ADD INDEX`` unsupported — index changes → rebuild, and the recreated
        table carries the new index set).
        """
        return True
