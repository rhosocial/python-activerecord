# src/rhosocial/activerecord/backend/dialect/mixins/ddl_column.py
"""DDL column formatting: column references, definitions, constraints, and
ALTER TABLE column/constraint actions."""

from typing import Any, Dict, List, Tuple, TYPE_CHECKING

from ...expression.bases import BaseExpression, ToSQLProtocol
from ...expression.core import Literal

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.core import Column
    from ...expression.statements.ddl_alter import (
        AddColumn,
        AddIndex,
        AddTableConstraint,
        AlterColumn,
        ChangeColumn,
        DropColumn,
        DropIndex,
        DropTableConstraint,
        ModifyColumn,
        RenameObject,
        RenameTable,
    )
    from ...expression.statements.ddl_table import (
        ColumnConstraint,
        ColumnDefinition,
        DefaultValueClause,
        IdentityClause,
        IndexDefinition,
        ReferencesClause,
        TableConstraint,
    )


class DDLColumnMixin:
    """Mixin for DDL column definition and ALTER TABLE action formatting."""

    def supports_foreign_key_on_delete(self) -> bool:
        """Whether FOREIGN KEY ON DELETE is supported (defaults to True)."""
        return True

    def supports_foreign_key_on_update(self) -> bool:
        """Whether FOREIGN KEY ON UPDATE is supported (defaults to True)."""
        return True

    def supports_fk_match(self) -> bool:
        """Whether FOREIGN KEY MATCH is supported (defaults to False)."""
        return False

    def supports_column_comment(self) -> bool:
        """Whether COLUMN COMMENT is supported (defaults to False)."""
        return False

    def supports_column_collation(self) -> bool:
        """Whether a column-level ``COLLATE <name>`` attribute is supported.

        Defaults to True — the SQL-standard form is valid on every backend
        that renders column definitions; backends whose column COLLATE is
        meaningless override this to return False.
        """
        return True

    def supports_column_character_set(self) -> bool:
        """Whether a column-level ``CHARACTER SET <name>`` attribute is
        supported.

        Defaults to False — character sets are a MySQL/MariaDB concept, not
        part of the generic dialect; those backends override this to return
        True.
        """
        return False

    def select_column_attributes(self, attributes: "List[Any]") -> "List[Any]":
        """Filter declared column attributes down to the renderable ones.

        The declared attributes are dialect-free (``ColumnAttribute``
        subclasses); selection follows the additive semantics (§5.6): a
        foreign-backend attribute is skipped, while an owned/generic
        attribute this dialect cannot render raises
        :class:`DeclarationSelectionError` — a declaration is never silently
        dropped.

        Per-kind capability switches: identity →
        :meth:`supports_auto_increment`, collation →
        :meth:`supports_column_collation`, character set →
        :meth:`supports_column_character_set`. Unknown kinds are backend
        extensions and render only on their owning backend.
        """
        from ....base.ddl.attributes import (
            CharacterSetAttribute,
            CollationAttribute,
            IdentityAttribute,
        )
        from ....base.ddl.selector import (
            DeclarationSelectionError,
            ExpressionOwnership,
        )

        ownership = ExpressionOwnership(self)
        selected: List[Any] = []
        for attr in attributes:
            classification = ownership.classify(type(attr))
            if classification == ExpressionOwnership.FOREIGN:
                continue
            kind = getattr(attr, "kind", "")
            if kind == "identity":
                renderable = self.supports_auto_increment()
            elif kind == "collation":
                renderable = self.supports_column_collation()
            elif kind == "character_set":
                renderable = self.supports_column_character_set()
            else:
                renderable = False
            if renderable:
                selected.append(attr)
            elif kind in ("identity", "collation", "character_set"):
                # Known generic kinds are capability-gated: the dialect skips
                # the ones it does not support (multi-backend candidates).
                continue
            else:
                # Unknown kinds are backend extensions: a generic-owned one
                # cannot render anywhere — error, never silent (§5.6).
                owner = ownership.owner_backend(type(attr))
                owner_label = f"backend {owner!r}" if owner else "core (generic)"
                raise DeclarationSelectionError(
                    "column_attributes",
                    [(type(attr).__name__, owner_label, "not supported by this dialect")],
                )
        return selected

    def format_column_attribute(self, attr: "Any") -> Tuple[str, Tuple]:
        """Render one selected column attribute as a definition fragment.

        Identity reuses :meth:`format_identity_clause` (per-backend syntax);
        collation renders the SQL-standard ``COLLATE <name>``. Backend-only
        kinds (or unknown kinds) raise ``UnsupportedFeatureError``.
        """
        from ....base.ddl.attributes import (
            CollationAttribute,
            IdentityAttribute,
        )
        from ...expression.statements.ddl_table import IdentityClause
        from ..exceptions import UnsupportedFeatureError

        if isinstance(attr, IdentityAttribute):
            clause = IdentityClause(
                self,
                attr.generation,
                start=attr.start,
                increment=attr.increment,
                minvalue=attr.minvalue,
                maxvalue=attr.maxvalue,
                cycle=attr.cycle,
            )
            return self.format_identity_clause(clause)
        if isinstance(attr, CollationAttribute):
            return f" COLLATE {attr.name}", ()
        raise UnsupportedFeatureError(
            self.name, f"COLUMN ATTRIBUTE {type(attr).__name__}",
            f"{self.name} cannot render the {type(attr).__name__} column "
            f"attribute; declare it only on backends that support it.",
        )

    def format_column(self, expr: "Column") -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.core.Column`.

        Renders an optional ``schema.table.column`` qualifier chain followed
        by an optional alias. Each component is quoted independently according
        to the expression's ``schema_need_quote``, ``table_need_quote``,
        ``name_need_quote``, and ``alias_need_quote`` fields.

        Args:
            expr: The column reference to render.

        Returns:
            A ``(sql, params)`` tuple. Column references never carry bind
            parameters, so ``params`` is always empty.
        """
        if expr.schema_name and expr.table:
            col_sql = (
                f"{self.format_identifier(expr.schema_name, expr.schema_need_quote)}."
                f"{self.format_identifier(expr.table, expr.table_need_quote)}."
                f"{self.format_identifier(expr.name, expr.name_need_quote)}"
            )
        elif expr.table:
            col_sql = (
                f"{self.format_identifier(expr.table, expr.table_need_quote)}."
                f"{self.format_identifier(expr.name, expr.name_need_quote)}"
            )
        else:
            col_sql = self.format_identifier(expr.name, expr.name_need_quote)

        if expr.alias:
            col_sql = f"{col_sql} AS {self.format_identifier(expr.alias, expr.alias_need_quote)}"
        return col_sql, ()

    def supports_add_column_if_not_exists(self) -> bool:
        """Whether ``ADD COLUMN IF NOT EXISTS`` is supported.

        Defaults to ``False``; backends that support the vendor extension
        override this to return ``True``.
        """
        return False

    def supports_drop_column_if_exists(self) -> bool:
        """Whether ``DROP COLUMN IF EXISTS`` is supported.

        Defaults to ``False``; backends that support the vendor extension
        override this to return ``True``.
        """
        return False

    def supports_drop_constraint_if_exists(self) -> bool:
        """Whether ``DROP CONSTRAINT IF EXISTS`` is supported.

        Defaults to ``False``; backends that support the vendor extension
        override this to return ``True``.
        """
        return False

    def format_identity_clause(self, expr: "IdentityClause") -> Tuple[str, Tuple]:
        """Format the SQL-standard identity clause.

        Renders `` GENERATED {ALWAYS|BY DEFAULT} AS IDENTITY`` with optional
        ``(START WITH ... INCREMENT BY ... MINVALUE ... MAXVALUE ... CYCLE ...)``.
        Backends with different syntax (MySQL ``AUTO_INCREMENT``, SQL Server
        ``IDENTITY(seed, inc)``, SQLite ``AUTOINCREMENT``) override this.

        Args:
            expr: The ``IdentityClause`` carrying the identity parameters.

        Returns:
            A ``(sql, params)`` tuple with a leading space.
        """
        generation = (expr.generation or "BY DEFAULT").upper()
        sql = f" GENERATED {generation} AS IDENTITY"
        attributes: List[str] = []
        if expr.start is not None:
            attributes.append(f"START WITH {expr.start}")
        if expr.increment is not None:
            attributes.append(f"INCREMENT BY {expr.increment}")
        if expr.minvalue is not None:
            attributes.append(f"MINVALUE {expr.minvalue}")
        if expr.maxvalue is not None:
            attributes.append(f"MAXVALUE {expr.maxvalue}")
        if expr.cycle is not None:
            attributes.append("CYCLE" if expr.cycle else "NO CYCLE")
        if attributes:
            sql += f" ({' '.join(attributes)})"
        return sql, ()

    def format_column_definition(self, col_def: "ColumnDefinition") -> Tuple[str, Tuple]:
        """Format a column definition clause (name, type, constraints, comment).

        Args:
            col_def: The column definition expression to render.

        Returns:
            A ``(sql, params)`` tuple. DDL accepts no bind parameters, so
            ``params`` is always empty.
        """
        all_params: List[Any] = []
        type_sql, _ = col_def.data_type.to_sql()
        col_sql = f"{self.format_identifier(col_def.name)} {type_sql}"

        for attr in col_def.attributes or ():
            # Dialect-free column attributes (identity, collation, character
            # set, …) selected by `select_column_attributes`; rendered through
            # `format_column_attribute`.
            attr_sql, attr_params = self.format_column_attribute(attr)
            col_sql += attr_sql
            all_params.extend(attr_params)
        for constraint in col_def.constraints:
            suffix, params = self.format_column_constraint(constraint)
            col_sql += suffix
            all_params.extend(params)

        if col_def.generated_expression is not None:
            gen_sql, gen_params = col_def.generated_expression.to_sql()
            col_sql += gen_sql
            all_params.extend(gen_params)

        if col_def.comment:
            if not self.supports_column_comment():
                from ..exceptions import UnsupportedFeatureError
                raise UnsupportedFeatureError(
                    self.name, "COLUMN COMMENT",
                    f"{self.name} does not support COLUMN COMMENT."
                )
            from ...dialect.base import SQLDialectBase as _B
            escaped_comment = _B._escape_sql_string(col_def.comment)
            col_sql += f" COMMENT '{escaped_comment}'"
        return col_sql, tuple(all_params)

    def format_generated_column_expression(self, expr) -> Tuple[str, Tuple]:
        """Format a :class:`~...statements.ddl_table.GeneratedColumnExpression`.

        Renders ``GENERATED ALWAYS AS (<expr>) STORED|VIRTUAL`` and delegates
        to :meth:`supports_generated_columns` /
        :meth:`supports_stored_generated_columns` /
        :meth:`supports_virtual_generated_columns` for capability gating.

        Backends that use non-standard syntax (e.g. Firebird's ``COMPUTED BY``)
        should override this method.

        Args:
            expr: The generated column expression to render.

        Returns:
            A ``(sql, params)`` tuple with a leading space.

        Raises:
            UnsupportedFeatureError: If generated columns (or the requested
                storage type) are not supported by this dialect.
        """
        from ...expression.statements.ddl_table import GeneratedColumnType
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_generated_columns():
            raise UnsupportedFeatureError(
                self.name,
                "Generated columns",
                f"{self.name} does not support generated (computed) columns.",
            )

        inner_sql, inner_params = expr.expression.to_sql()

        if expr.storage_type == GeneratedColumnType.STORED:
            if not self.supports_stored_generated_columns():
                raise UnsupportedFeatureError(
                    self.name,
                    "STORED generated columns",
                    f"{self.name} does not support STORED generated columns.",
                )
            storage = " STORED"
        else:
            if not self.supports_virtual_generated_columns():
                raise UnsupportedFeatureError(
                    self.name,
                    "VIRTUAL generated columns",
                    f"{self.name} does not support VIRTUAL generated columns.",
                )
            storage = " VIRTUAL"

        return f" GENERATED ALWAYS AS ({inner_sql}){storage}", inner_params

    def format_column_constraint(self, constraint: "ColumnConstraint") -> Tuple[str, Tuple]:
        """Format a single column constraint clause.

        Dispatches to the specialised formatter for the constraint type.
        Simple constraints (PRIMARY KEY, NOT NULL, NULL, UNIQUE) are rendered
        directly.

        Args:
            constraint: The column constraint expression to render.

        Returns:
            A ``(sql, params)`` tuple. The ``sql`` value is prefixed with a
            leading space so it can be appended directly to a column definition.
        """
        from ...expression.statements import ColumnConstraintType
        ctype = constraint.constraint_type
        simple_constraints = {
            ColumnConstraintType.PRIMARY_KEY: " PRIMARY KEY",
            ColumnConstraintType.NOT_NULL: " NOT NULL",
            ColumnConstraintType.NULL: " NULL",
            ColumnConstraintType.UNIQUE: " UNIQUE",
        }
        if ctype in simple_constraints:
            return simple_constraints[ctype], ()
        if ctype == ColumnConstraintType.DEFAULT:
            return self.format_default_constraint(constraint)
        if ctype == ColumnConstraintType.CHECK:
            return self.format_column_check_constraint(constraint)
        if ctype == ColumnConstraintType.FOREIGN_KEY:
            return self.format_column_fk_constraint(constraint)
        return "", ()

    def format_column_check_constraint(self, constraint: "ColumnConstraint") -> Tuple[str, Tuple]:
        """Format a column-level ``CHECK`` constraint.

        Args:
            constraint: The constraint whose ``check_condition`` is rendered.

        Returns:
            A ``(sql, params)`` tuple with a leading space.
        """
        if constraint.check_condition is None:
            return "", ()
        check_sql, check_params = constraint.check_condition.to_sql()
        return f" CHECK ({check_sql})", tuple(check_params)

    def format_default_value_clause(self, expr: "DefaultValueClause") -> Tuple[str, Tuple]:
        """Format the value clause of a ``DEFAULT`` constraint.

        Scalars are inlined with dialect-controlled escaping; a
        ``BaseExpression`` value renders through its own ``to_sql`` (a
        parameterised ``Literal`` is inlined so DDL carries no bind params).

        Args:
            expr: The ``DefaultValueClause`` carrying the value.

        Returns:
            A ``(sql, params)`` tuple (params is always empty for DDL).
        """
        from ...dialect.base import SQLDialectBase
        value = expr.value
        if isinstance(value, BaseExpression):
            value_sql, value_params = value.to_sql()
            if value_params and isinstance(value, Literal):
                # A parameterized literal inside DDL: re-render inline.
                value_sql = self.inline_sql_literal(value.value)
                value_params = ()
            return value_sql, tuple(value_params)
        if isinstance(value, str):
            escaped = SQLDialectBase._escape_sql_string(value)
            return f"'{escaped}'", ()
        return self.inline_sql_literal(value), ()

    def format_default_constraint(self, constraint: "ColumnConstraint") -> Tuple[str, Tuple]:
        """Format a ``DEFAULT`` constraint.

        The default value is always rendered inline (DDL carries no bind
        parameters); value rendering is delegated to
        :meth:`format_default_value_clause`.

        Args:
            constraint: The constraint whose ``default_value`` is rendered.

        Returns:
            A ``(sql, params)`` tuple with a leading space.

        Raises:
            ValueError: If ``default_value`` is ``None``.
        """
        from ...expression.statements.ddl_table import DefaultValueClause
        if constraint.default_value is None:
            raise ValueError("DEFAULT constraint must have a default value specified.")
        if isinstance(constraint.default_value, DefaultValueClause):
            value_clause = constraint.default_value
        else:
            value_clause = DefaultValueClause(self, constraint.default_value)
        value_sql, value_params = self.format_default_value_clause(value_clause)
        return f" DEFAULT {value_sql}", tuple(value_params)

    def format_references_clause(self, expr: "ReferencesClause") -> Tuple[str, Tuple]:
        """Format a ``REFERENCES`` clause (shared by column/table foreign keys).

        Renders ``REFERENCES <table>(<cols>)`` plus the referential actions and
        deferrability. Backends with different syntax override this.

        Args:
            expr: The ``ReferencesClause`` carrying the referenced table/columns
                and optional actions.

        Returns:
            A ``(sql, params)`` tuple (params is always empty for DDL).

        Raises:
            ValueError: If the referenced table has no columns.
        """
        from ...expression.statements import ReferentialAction
        if not expr.referenced_columns:
            raise ValueError("REFERENCES clause requires at least one referenced column.")
        ref_cols_str = ", ".join(self.format_identifier(col) for col in expr.referenced_columns)
        result = f"REFERENCES {self.format_identifier(expr.referenced_table)}({ref_cols_str})"
        if expr.match_type is not None:
            if not self.supports_fk_match():
                from ..exceptions import UnsupportedFeatureError
                raise UnsupportedFeatureError(
                    self.name, "FOREIGN KEY MATCH",
                    f"{self.name} does not support MATCH for foreign keys."
                )
            result += f" MATCH {expr.match_type}"
        if expr.on_delete is not None and expr.on_delete != ReferentialAction.NO_ACTION:
            if not self.supports_foreign_key_on_delete():
                from ..exceptions import UnsupportedFeatureError
                raise UnsupportedFeatureError(
                    self.name, "FOREIGN KEY ON DELETE",
                    f"{self.name} does not support ON DELETE for foreign keys."
                )
            result += f" ON DELETE {self._referential_action_value(expr.on_delete)}"
        if expr.on_update is not None and expr.on_update != ReferentialAction.NO_ACTION:
            if not self.supports_foreign_key_on_update():
                from ..exceptions import UnsupportedFeatureError
                raise UnsupportedFeatureError(
                    self.name, "FOREIGN KEY ON UPDATE",
                    f"{self.name} does not support ON UPDATE for foreign keys."
                )
            result += f" ON UPDATE {self._referential_action_value(expr.on_update)}"
        if expr.deferrable is True:
            if expr.initially_deferred is True:
                result += " DEFERRABLE INITIALLY DEFERRED"
            elif expr.initially_deferred is False:
                result += " DEFERRABLE INITIALLY IMMEDIATE"
            else:
                result += " DEFERRABLE"
        elif expr.deferrable is False:
            result += " NOT DEFERRABLE"
        return result, ()

    @staticmethod
    def _referential_action_value(action: Any) -> str:
        """Normalise a referential action to its SQL keyword."""
        return action.value if hasattr(action, "value") else str(action)

    def format_column_fk_constraint(self, constraint: "ColumnConstraint") -> Tuple[str, Tuple]:
        """Format a column-level ``REFERENCES`` (foreign key) constraint.

        Delegates the reference body to :meth:`format_references_clause`.

        Args:
            constraint: The constraint whose ``foreign_key_reference`` is
                rendered.

        Returns:
            A ``(sql, params)`` tuple with a leading space.

        Raises:
            ValueError: If ``foreign_key_reference`` is ``None``.
        """
        if constraint.foreign_key_reference is None:
            raise ValueError("Foreign key constraint must have a foreign_key_reference specified.")
        referenced_table, referenced_columns = constraint.foreign_key_reference
        from ...expression.statements.ddl_table import ReferencesClause
        references = ReferencesClause(
            self,
            referenced_table,
            referenced_columns,
            on_delete=constraint.on_delete,
            on_update=constraint.on_update,
            deferrable=constraint.deferrable,
            initially_deferred=constraint.initially_deferred,
        )
        ref_sql, ref_params = self.format_references_clause(references)
        return f" {ref_sql}", tuple(ref_params)

    def format_pk_constraint(self, t_const: "TableConstraint") -> Tuple[str, tuple]:
        """Format the body of a ``PRIMARY KEY`` table constraint.

        Args:
            t_const: The constraint whose ``columns`` are rendered.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            ValueError: If no columns are specified.
        """
        if not t_const.columns:
            raise ValueError("PRIMARY KEY constraint must have at least one column specified.")
        cols_str = ", ".join(self.format_identifier(col) for col in t_const.columns)
        return f"PRIMARY KEY ({cols_str})", ()

    def format_unique_constraint(self, t_const: "TableConstraint") -> Tuple[str, tuple]:
        """Format the body of a ``UNIQUE`` table constraint.

        Args:
            t_const: The constraint whose ``columns`` are rendered.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            ValueError: If no columns are specified.
        """
        if not t_const.columns:
            raise ValueError("UNIQUE constraint must have at least one column specified.")
        cols_str = ", ".join(self.format_identifier(col) for col in t_const.columns)
        return f"UNIQUE ({cols_str})", ()

    def format_table_check_constraint(self, t_const: "TableConstraint") -> Tuple[str, Tuple]:
        """Format a table-level ``CHECK`` constraint body.

        Args:
            t_const: The constraint whose ``check_condition`` is rendered.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            ValueError: If ``check_condition`` is ``None``.
        """
        if t_const.check_condition is None:
            raise ValueError("CHECK constraint must have a check condition specified.")
        check_sql, check_params = t_const.check_condition.to_sql()
        return f"CHECK ({check_sql})", tuple(check_params)

    def format_foreign_key_constraint(self, t_const: "TableConstraint") -> Tuple[str, Tuple]:
        """Format a table-level ``FOREIGN KEY`` constraint body.

        Args:
            t_const: The constraint carrying the local columns, referenced
                table, and referenced columns.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            ValueError: If local columns, foreign key columns, or the
                referenced table are missing.
        """
        if not t_const.columns:
            raise ValueError("FOREIGN KEY constraint must have at least one local column specified.")
        if not t_const.foreign_key_columns:
            raise ValueError("FOREIGN KEY constraint must have at least one foreign key column specified.")
        if not t_const.foreign_key_table:
            raise ValueError("FOREIGN KEY constraint must have a foreign key table specified.")
        cols_str = ", ".join(self.format_identifier(col) for col in t_const.columns)
        from ...expression.statements import ForeignKeyConstraint
        from ...expression.statements.ddl_table import ReferencesClause
        if isinstance(t_const, ForeignKeyConstraint):
            on_delete = t_const.on_delete
            on_update = t_const.on_update
            match_type = t_const.match_type
        else:
            on_delete = on_update = match_type = None
        references = ReferencesClause(
            self,
            t_const.foreign_key_table,
            list(t_const.foreign_key_columns),
            on_delete=on_delete,
            on_update=on_update,
            match_type=match_type,
            deferrable=t_const.deferrable,
            initially_deferred=t_const.initially_deferred,
        )
        ref_sql, ref_params = self.format_references_clause(references)
        return f"FOREIGN KEY ({cols_str}) {ref_sql}", tuple(ref_params)

    def format_table_constraint(self, expr: "TableConstraint") -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.statements.TableConstraint` clause.

        Renders the optional ``CONSTRAINT <name>`` prefix followed by the
        type-specific body (PRIMARY KEY, UNIQUE, CHECK, or FOREIGN KEY).

        Args:
            expr: The table constraint expression to render.

        Returns:
            A ``(sql, params)`` tuple; ``sql`` is empty when no clause parts
            are produced.
        """
        from ...expression.statements import TableConstraintType
        const_parts = []
        params: Tuple = ()
        if expr.name:
            const_parts.append(f"CONSTRAINT {self.format_identifier(expr.name)}")
        ctype = expr.constraint_type
        if ctype == TableConstraintType.PRIMARY_KEY:
            pk_sql, _ = self.format_pk_constraint(expr)
            const_parts.append(pk_sql)
        elif ctype == TableConstraintType.UNIQUE:
            unique_sql, _ = self.format_unique_constraint(expr)
            const_parts.append(unique_sql)
        elif ctype == TableConstraintType.CHECK:
            sql, params = self.format_table_check_constraint(expr)
            const_parts.append(sql)
        elif ctype == TableConstraintType.FOREIGN_KEY:
            fk_sql, _ = self.format_foreign_key_constraint(expr)
            const_parts.append(fk_sql)
        return " ".join(const_parts) if const_parts else "", tuple(params)

    def format_storage_options(self, expr: "StorageOptionsExpression") -> Tuple[str, tuple]:
        """Format a ``WITH (...)`` storage-options clause.

        Each option value is rendered as an inline SQL literal via
        ``inline_sql_literal``.

        Args:
            expr: A :class:`StorageOptionsExpression` holding the options mapping.

        Returns:
            A ``(sql, params)`` tuple; ``sql`` is empty when the mapping is
            empty.
        """
        storage_parts = []
        for key, value in expr.options.items():
            quoted_key = self.format_identifier(key)
            rendered_value = self.inline_sql_literal(value)
            storage_parts.append(f"{quoted_key} = {rendered_value}")
        if storage_parts:
            return " WITH (" + ", ".join(storage_parts) + ")", ()
        return "", ()

    def format_add_column_action(self, action: "AddColumn") -> Tuple[str, Tuple]:
        """Format an ``ADD COLUMN`` ALTER TABLE action.

        Args:
            action: The action carrying the column definition to add.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            UnsupportedFeatureError: If IF NOT EXISTS is requested but not
                supported by the dialect.
        """
        from ..exceptions import UnsupportedFeatureError
        column_sql, column_params = self.format_column_definition(action.column)
        if getattr(action, "if_not_exists", None):
            if not self.supports_add_column_if_not_exists():
                raise UnsupportedFeatureError(
                    self.name, "ADD COLUMN IF NOT EXISTS",
                    f"{self.name} does not support ADD COLUMN IF NOT EXISTS."
                )
            return f"ADD COLUMN IF NOT EXISTS {column_sql}", column_params
        return f"ADD COLUMN {column_sql}", column_params

    def format_drop_column_action(self, action: "DropColumn") -> Tuple[str, Tuple]:
        """Format a ``DROP COLUMN`` ALTER TABLE action.

        Emits ``DROP COLUMN IF EXISTS`` when the action requests it.

        Args:
            action: The action carrying the column name to drop.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.

        Raises:
            UnsupportedFeatureError: If IF EXISTS is requested but not
                supported by the dialect.
        """
        from ..exceptions import UnsupportedFeatureError
        if hasattr(action, "if_exists") and action.if_exists:
            if not self.supports_drop_column_if_exists():
                raise UnsupportedFeatureError(
                    self.name, "DROP COLUMN IF EXISTS",
                    f"{self.name} does not support DROP COLUMN IF EXISTS."
                )
            return f"DROP COLUMN IF EXISTS {self.format_identifier(action.column_name)}", ()
        return f"DROP COLUMN {self.format_identifier(action.column_name)}", ()

    def format_alter_column_action(self, action: "AlterColumn") -> Tuple[str, Tuple]:
        """Format an ``ALTER COLUMN`` ALTER TABLE action.

        Handles ``SET DATA TYPE`` (validated type text), string values
        (escaped and inlined), expression values rendered through
        ``to_sql``, and plain values inlined via ``inline_sql_literal``.

        Args:
            action: The action carrying the column name, operation, and
                optional new value.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            ValueError: If a ``SET DATA TYPE`` value is not a valid data type
                specification.
        """
        all_params: List[Any] = []
        operation_str = action.operation.value if hasattr(action.operation, "value") else str(action.operation)
        column_part = f"ALTER COLUMN {self.format_identifier(action.column_name)} {operation_str}"
        if hasattr(action, "new_value") and action.new_value is not None:
            if operation_str == "SET DATA TYPE":
                from ...dialect.base import SQLDialectBase
                if not SQLDialectBase._validate_data_type(str(action.new_value)):
                    raise ValueError(f"Invalid data type specification: '{action.new_value}'")
                column_part += f" {action.new_value}"
            elif isinstance(action.new_value, str):
                # DDL accepts no bind parameters: inline with escaping.
                from ...dialect.base import SQLDialectBase
                column_part += f" '{SQLDialectBase._escape_sql_string(action.new_value)}'"
            elif isinstance(action.new_value, ToSQLProtocol):
                value_sql, value_params = action.new_value.to_sql()
                if value_params:
                    # Parameterized literal inside DDL → render inline.
                    if isinstance(action.new_value, Literal):
                        value_sql = self.inline_sql_literal(action.new_value.value)
                        value_params = ()
                column_part += f" {value_sql}"
                all_params.extend(value_params)
            else:
                column_part += f" {self.inline_sql_literal(action.new_value)}"
        if hasattr(action, "cascade") and action.cascade:
            column_part += " CASCADE"
        return column_part, tuple(all_params)

    def format_add_table_constraint_action(self, action: "AddTableConstraint") -> Tuple[str, Tuple]:
        """Format an ``ADD CONSTRAINT`` ALTER TABLE action.

        Args:
            action: The action carrying the table constraint to add.

        Returns:
            A ``(sql, params)`` tuple prefixed with ``ADD``.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                ``ALTER TABLE ADD CONSTRAINT``.
            ValueError: If a ``MATCH`` type on a foreign key is invalid.
        """
        from ...expression.statements import TableConstraintType, ReferentialAction, ForeignKeyConstraint
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_add_constraint():
            raise UnsupportedFeatureError(self.name, "ALTER TABLE ADD CONSTRAINT")
        all_params: List[Any] = []
        parts = []
        if action.constraint.name:
            parts.append(f"CONSTRAINT {self.format_identifier(action.constraint.name)}")
        ctype = action.constraint.constraint_type
        if ctype == TableConstraintType.PRIMARY_KEY:
            if action.constraint.columns:
                cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.columns)
                parts.append(f"PRIMARY KEY ({cols_str})")
            else:
                parts.append("PRIMARY KEY")
        elif ctype == TableConstraintType.UNIQUE:
            if action.constraint.columns:
                cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.columns)
                parts.append(f"UNIQUE ({cols_str})")
            else:
                parts.append("UNIQUE")
        elif ctype == TableConstraintType.CHECK and action.constraint.check_condition:
            check_sql, check_params = action.constraint.check_condition.to_sql()
            parts.append(f"CHECK ({check_sql})")
            all_params.extend(check_params)
        elif ctype == TableConstraintType.FOREIGN_KEY:
            if action.constraint.columns and action.constraint.foreign_key_table:
                cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.columns)
                ref_table = self.format_identifier(action.constraint.foreign_key_table)
                ref_cols_str = (
                    ", ".join(self.format_identifier(col) for col in action.constraint.foreign_key_columns)
                    if action.constraint.foreign_key_columns
                    else ""
                )
                if ref_cols_str:
                    parts.append(f"FOREIGN KEY ({cols_str}) REFERENCES {ref_table}({ref_cols_str})")
                else:
                    parts.append(f"FOREIGN KEY ({cols_str}) REFERENCES {ref_table}")
            else:
                parts.append("FOREIGN KEY")
            if isinstance(action.constraint, ForeignKeyConstraint):
                if action.constraint.match_type:
                    _VALID_MATCH_TYPES = frozenset({"SIMPLE", "PARTIAL", "FULL"})
                    mt = action.constraint.match_type.upper()
                    if mt not in _VALID_MATCH_TYPES:
                        raise ValueError(
                            f"Invalid MATCH type '{action.constraint.match_type}'. "
                            f"Must be one of: {', '.join(sorted(_VALID_MATCH_TYPES))}"
                        )
                    parts.append(f"MATCH {mt}")
                if action.constraint.on_delete != ReferentialAction.NO_ACTION:
                    parts.append(f"ON DELETE {action.constraint.on_delete.value}")
                if action.constraint.on_update != ReferentialAction.NO_ACTION:
                    parts.append(f"ON UPDATE {action.constraint.on_update.value}")
        else:
            parts.append("UNKNOWN CONSTRAINT")
        if action.constraint.deferrable is True:
            if action.constraint.initially_deferred is True:
                parts.append("DEFERRABLE INITIALLY DEFERRED")
            elif action.constraint.initially_deferred is False:
                parts.append("DEFERRABLE INITIALLY IMMEDIATE")
            else:
                parts.append("DEFERRABLE")
        elif action.constraint.deferrable is False:
            parts.append("NOT DEFERRABLE")
        return f"ADD {' '.join(parts)}", tuple(all_params)

    def format_drop_table_constraint_action(self, action: "DropTableConstraint") -> Tuple[str, Tuple]:
        """Format a ``DROP CONSTRAINT`` ALTER TABLE action.

        Args:
            action: The action carrying the constraint name and optional
                cascade flag.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                ``ALTER TABLE DROP CONSTRAINT``.
        """
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_drop_constraint():
            raise UnsupportedFeatureError(self.name, "ALTER TABLE DROP CONSTRAINT")
        result = f"DROP CONSTRAINT {self.format_identifier(action.constraint_name)}"
        if hasattr(action, "cascade") and action.cascade:
            result += " CASCADE"
        return result, ()

    def format_index_definition(self, expr: "IndexDefinition") -> Tuple[str, Tuple]:
        """Format an :class:`~...expression.statements.IndexDefinition` clause.

        Args:
            expr: The index definition carrying name, columns, uniqueness,
                and optional index type.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.
        """
        if expr.type and not self.supports_index_type():
            from ..exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name, "index type (USING)",
                f"{self.name} does not support index types.",
            )
        all_params: List[Any] = []
        col_parts = []
        for col in expr.columns:
            if isinstance(col, ToSQLProtocol):
                col_sql, col_params = col.to_sql()
                col_parts.append(col_sql)
                all_params.extend(col_params)
            else:
                col_parts.append(self.format_identifier(str(col)))
        cols_str = ", ".join(col_parts)
        unique_str = "UNIQUE " if expr.unique else ""
        type_str = f" USING {expr.type}" if expr.type else ""
        return (
            f"{unique_str}{self.format_identifier(expr.name)}{type_str} ({cols_str})",
            tuple(all_params),
        )

    def format_add_index_action(self, action: "AddIndex") -> Tuple[str, Tuple]:
        """Format an ``ADD INDEX`` ALTER TABLE action.

        Args:
            action: The action carrying the index definition to add.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.
        """
        columns = ", ".join(
            self.format_identifier(col) for col in action.index.columns
        )
        return (
            f"ADD INDEX {self.format_identifier(action.index.name)} ({columns})",
            (),
        )

    def format_drop_index_action(self, action: "DropIndex") -> Tuple[str, Tuple]:
        """Format a ``DROP INDEX`` ALTER TABLE action.

        Emits ``DROP INDEX IF EXISTS`` when the action requests it.

        Args:
            action: The action carrying the index name to drop.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.
        """
        if hasattr(action, "if_exists") and action.if_exists:
            return f"DROP INDEX IF EXISTS {self.format_identifier(action.index_name)}", ()
        return f"DROP INDEX {self.format_identifier(action.index_name)}", ()

    def format_rename_column_action(self, action: "RenameObject") -> Tuple[str, Tuple]:
        """Format a ``RENAME COLUMN`` ALTER TABLE action.

        Args:
            action: The action carrying the old and new column names.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.
        """
        return (
            f"RENAME COLUMN {self.format_identifier(action.old_name)} TO {self.format_identifier(action.new_name)}",
            (),
        )

    def format_rename_table_action(self, action: "RenameTable") -> Tuple[str, Tuple]:
        """Format a ``RENAME TO`` ALTER TABLE action.

        Args:
            action: The action carrying the new table name.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.
        """
        return f"RENAME TO {self.format_identifier(action.new_name)}", ()

    def format_modify_column_action(self, action: "ModifyColumn") -> Tuple[str, Tuple]:
        """Format a ``MODIFY COLUMN`` ALTER TABLE action.

        The core implementation always raises, since ``MODIFY COLUMN`` is
        MySQL/MariaDB-specific; those backends override this method.

        Args:
            action: The action carrying the column definition to apply.

        Raises:
            UnsupportedFeatureError: Always, at the core layer.
        """
        from ..exceptions import UnsupportedFeatureError
        raise UnsupportedFeatureError(self.name, "MODIFY COLUMN")

    def format_change_column_action(self, action: "ChangeColumn") -> Tuple[str, Tuple]:
        """Format a ``CHANGE COLUMN`` ALTER TABLE action.

        The core implementation always raises, since ``CHANGE COLUMN`` is
        MySQL/MariaDB-specific; those backends override this method.

        Args:
            action: The action carrying the old name and new column definition.

        Raises:
            UnsupportedFeatureError: Always, at the core layer.
        """
        from ..exceptions import UnsupportedFeatureError
        raise UnsupportedFeatureError(self.name, "CHANGE COLUMN")
