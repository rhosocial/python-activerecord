# src/rhosocial/activerecord/ddl/active.py
"""Source-bound DDL expression factories.

``ActiveDDL`` and ``AsyncActiveDDL`` are thin public façades over
:class:`~rhosocial.activerecord.ddl.deriver.TableDDLDeriver`.  They read
Dialect-free declarations from a :class:`~rhosocial.activerecord.base.ddl.DDLSource`,
combine them with the dialect exposed by a storage backend, and return
concrete DDL expression objects.

The factories cover the source-bound subset of table, index, view, comment,
alter, and truncate generation.  They do not produce final SQL, execute DDL,
create plans, or provide compatibility code.  Selection may perform a
transient ``to_sql()`` renderability probe, while final SQL and feature-specific
capability errors remain in the backend formatter.  Source-shape and selection
errors are raised while building the expression.
"""

from __future__ import annotations

from typing import Optional, Sequence, Union, TYPE_CHECKING

from rhosocial.activerecord.backend.base import AsyncStorageBackend, StorageBackend
from rhosocial.activerecord.backend.expression.bases import BaseExpression, SQLPredicate
from rhosocial.activerecord.backend.expression.statements.ddl_alter import AlterTableAction, AlterTableExpression
from rhosocial.activerecord.backend.expression.statements.ddl_comment import CommentObjectType, CommentOnExpression
from rhosocial.activerecord.backend.expression.statements.ddl_index import CreateIndexExpression, DropIndexExpression
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableExpression,
    DropTableExpression,
    IndexDefinition,
)
from rhosocial.activerecord.backend.expression.statements.ddl_truncate import TruncateExpression
from rhosocial.activerecord.backend.expression.statements.ddl_view import CreateViewExpression, DropViewExpression
from rhosocial.activerecord.base.ddl import DDLSource as _DDLSource
from .deriver import TableDDLDeriver
from .partition import PartitionLifecycle

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements.ddl_view import ColumnAlias, ViewOptions
    from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression


class _ActiveDDLCore:
    """Shared implementation for the synchronous and asynchronous façades.

    The backend object is used only to obtain ``backend.dialect``; this class
    does not call backend connection, transaction, or execution methods.  The
    source remains the sole source of table and column declarations.
    """

    def __init__(
        self,
        source: _DDLSource,
        backend: Union[StorageBackend, AsyncStorageBackend],
    ):
        """Create a source-bound factory for a backend dialect.

        Args:
            source: Structural DDL declaration source, such as an
                ``ActiveRecord`` model or a compatible implementation of
                :class:`~rhosocial.activerecord.base.ddl.DDLSource`.
            backend: Synchronous or asynchronous storage backend whose
                ``dialect`` attribute supplies SQL capability and formatting
                behavior.

        Notes:
            No database connection is opened and no backend operation is
            invoked during construction.
        """
        self.source = source
        self.backend = backend
        self.dialect = backend.dialect
        self.deriver = TableDDLDeriver(source, self.dialect)

    def partition_lifecycle(self) -> PartitionLifecycle:
        """Return a source-bound partition lifecycle expression factory.

        Returns:
            A facade bound to this DDL source and dialect.  It only constructs
            backend partition expressions and never executes them.
        """
        return PartitionLifecycle(self.source, self.dialect)

    def _declared_index(self, index_name: Optional[str]) -> IndexDefinition:
        """Resolve one source-declared index for a convenience overload.

        Args:
            index_name: Name of the declaration to find, or ``None`` to use
                the only declared index.

        Returns:
            The selected dialect-bound ``IndexDefinition``.

        Raises:
            ValueError: If ``index_name`` is ``None`` and the source does not
                declare exactly one index.
            KeyError: If the named index is not present in the merged source
                declarations.
            DeclarationSelectionError: Propagated from the deriver when a
                declared index is not applicable to the active dialect.
        """
        indexes = self.deriver.indexes()
        if index_name is None:
            if len(indexes) != 1:
                raise ValueError(
                    "index_name is required when the source does not declare exactly one index"
                )
            return indexes[0]
        for index in indexes:
            if index.name == index_name:
                return index
        raise KeyError(f"index is not declared by the source: {index_name}")

    def create_table(
        self,
        *,
        if_not_exists: bool = False,
        temporary: bool = False,
        inline_indexes: Optional[bool] = None,
    ) -> CreateTableExpression:
        """Build a source-derived ``CREATE TABLE`` expression.

        Args:
            if_not_exists: Add the ``IF NOT EXISTS`` qualifier to the
                returned statement expression.
            temporary: Request a temporary table when the dialect supports
                that form.
            inline_indexes: Whether to include declared indexes in the table
                expression.  ``None`` follows the dialect's
                ``supports_inline_index()`` capability; ``True`` forces the
                inline path; ``False`` omits indexes from this expression.

        Returns:
            A dialect-bound ``CreateTableExpression`` containing the source's
            physical columns, selected constraints, options, and partition
            declaration.

        Raises:
            DeclarationSelectionError: If a required declaration has no
                applicable candidate for the active dialect.
            ValueError: If inline indexes carry statement-level options that
                cannot be represented inside ``CREATE TABLE``.
            ColumnTypeResolutionError: If a physical field's type cannot be
                resolved.
            StatementContractError: If the selected statement class does not
                accept the canonical CREATE TABLE parameters.

        Notes:
            Forcing ``inline_indexes=True`` can construct an expression on a
            dialect that cannot render inline indexes; the backend formatter
            reports that capability error when the expression is rendered.
        """
        return self.deriver.create_table(
            if_not_exists=if_not_exists,
            temporary=temporary,
            inline_indexes=inline_indexes,
        )

    def create_index(
        self,
        index_name: Optional[str] = None,
        columns: Optional[Sequence[Union[str, BaseExpression]]] = None,
        *,
        unique: Optional[bool] = None,
        if_not_exists: Optional[bool] = None,
        index_type: Optional[str] = None,
        where: Optional[SQLPredicate] = None,
        include: Optional[Sequence[str]] = None,
        tablespace: Optional[str] = None,
        concurrent: Optional[bool] = None,
    ) -> CreateIndexExpression:
        """Build a standalone ``CREATE INDEX`` expression.

        Args:
            index_name: Index name.  When omitted, the source must declare
                exactly one index; when supplied with omitted ``columns``,
                the named declaration supplies the remaining defaults.
            columns: Column names or expression-valued index keys.  When
                omitted, the selected source declaration supplies them.
            unique: Whether the index is unique.  ``None`` inherits the
                declaration's value or defaults to ``False`` for a manual
                index.
            if_not_exists: Add the create-if-not-exists option.  ``None``
                inherits the declaration's value or defaults to ``False``.
            index_type: Optional backend index type, such as ``BTREE`` or
                ``HASH``.
            where: Optional partial-index predicate.
            include: Optional covering/include column names.
            tablespace: Optional index tablespace name.
            concurrent: Request concurrent index creation.  ``None`` inherits
                the declaration's value or defaults to ``False``.

        Returns:
            A dialect-bound ``CreateIndexExpression`` targeting the source
            table.  Non-``None`` explicit arguments take precedence over
            inherited declaration values.

        Raises:
            ValueError: If a name or column list is missing and cannot be
                inferred from exactly one source index declaration.
            KeyError: If an explicitly supplied name is used to infer columns
                but no such index is declared.
            DeclarationSelectionError: Propagated when the source index
                declaration is not applicable to the active dialect.
        """
        definition = None
        if index_name is None or columns is None:
            definition = self._declared_index(index_name)
        if index_name is None:
            if definition is None:
                raise ValueError("index_name is required")
            index_name = definition.name
        if columns is None:
            if definition is None:
                raise ValueError("columns are required for a manual index")
            columns = definition.columns
        if unique is None:
            unique = definition.unique if definition is not None else False
        if if_not_exists is None:
            if_not_exists = bool(definition.if_not_exists) if definition is not None else False
        if index_type is None and definition is not None:
            index_type = definition.type
        if where is None and definition is not None:
            where = definition.partial_condition
        if include is None and definition is not None:
            include = definition.include_columns
        if tablespace is None and definition is not None:
            tablespace = definition.tablespace
        if concurrent is None:
            concurrent = bool(definition.concurrent) if definition is not None else False
        return CreateIndexExpression(
            self.dialect,
            index_name=index_name,
            table_name=self.source.table_name(),
            columns=list(columns),
            unique=unique,
            if_not_exists=if_not_exists,
            index_type=index_type,
            where=where,
            include=list(include) if include is not None else None,
            tablespace=tablespace,
            concurrent=concurrent,
        )

    def drop_index(
        self,
        index_name: Optional[str] = None,
        *,
        table_name: Optional[str] = None,
        if_exists: bool = False,
        concurrent: bool = False,
    ) -> DropIndexExpression:
        """Build a standalone ``DROP INDEX`` expression.

        Args:
            index_name: Index name.  If omitted, the source must declare
                exactly one index and that declaration supplies the name.
            table_name: Optional table context for dialects that require or
                accept ``DROP INDEX ... ON <table>``.  An empty or ``None``
                value falls back to the source table name.
            if_exists: Add the drop-if-exists option.
            concurrent: Request concurrent index removal.

        Returns:
            A dialect-bound ``DropIndexExpression`` carrying the requested
            index and table context.

        Raises:
            ValueError: If ``index_name`` is omitted and the source does not
                declare exactly one index.
            KeyError: If a name lookup is required but the named declaration
                is absent.
            DeclarationSelectionError: Propagated from source index
                collection when the declared index is not applicable.
        """
        if index_name is None:
            index_name = self._declared_index(None).name
        return DropIndexExpression(
            self.dialect,
            index_name=index_name,
            table_name=table_name or self.source.table_name(),
            if_exists=if_exists,
            concurrent=concurrent,
        )

    def alter_table(
        self,
        actions: Optional[Sequence[AlterTableAction]] = None,
    ) -> AlterTableExpression:
        """Build an ``ALTER TABLE`` expression for the source table.

        Args:
            actions: Ordered ``AlterTableAction`` expressions to apply.  An
                omitted or empty sequence produces an action-less statement
                expression.

        Returns:
            A dialect-bound ``AlterTableExpression`` targeting the source
            table name and carrying a copy of the action sequence.

        Raises:
            TypeError: If any supplied action is not an
                ``AlterTableAction`` instance.

        Notes:
            Dialect support for individual actions and vendor qualifiers is
            checked by the backend formatter when the expression is rendered.
        """
        return AlterTableExpression(
            self.dialect,
            table_name=self.source.table_name(),
            actions=list(actions or ()),
        )

    def drop_table(
        self,
        *,
        if_exists: bool = False,
        cascade: Optional[bool] = None,
        purge: bool = False,
    ) -> DropTableExpression:
        """Build a source-bound ``DROP TABLE`` expression.

        Args:
            if_exists: Add the ``IF EXISTS`` qualifier.
            cascade: ``None`` leaves the dialect default unspecified, ``True``
                requests cascade behavior, and ``False`` requests restrict
                behavior where the dialect supports it.
            purge: Request a backend-specific purge option, commonly used by
                Oracle-compatible dialects.

        Returns:
            A dialect-bound ``DropTableExpression`` targeting the source table.

        Notes:
            ``CASCADE``, ``RESTRICT``, ``IF EXISTS``, and ``PURGE`` are
            capability-gated by the dialect formatter rather than by this
            generation-only façade.
        """
        return self.deriver.drop_table(
            if_exists=if_exists,
            cascade=cascade,
            purge=purge,
        )

    def truncate(
        self,
        *,
        restart_identity: bool = False,
        cascade: bool = False,
    ) -> TruncateExpression:
        """Build a source-bound ``TRUNCATE TABLE`` expression.

        Args:
            restart_identity: Request resetting identity/auto-increment
                counters where the dialect supports ``RESTART IDENTITY``.
            cascade: Request truncation of dependent objects where the dialect
                supports that option.

        Returns:
            A dialect-bound ``TruncateExpression`` targeting the source table
            with the requested flags.

        Notes:
            Option support is a dialect concern; this method only carries the
            flags into the returned expression.
        """
        return self.deriver.truncate(
            restart_identity=restart_identity,
            cascade=cascade,
        )

    def comment_on(
        self,
        object_type: Union[CommentObjectType, str] = CommentObjectType.TABLE,
        object_name: Optional[str] = None,
        comment: Optional[str] = None,
        *,
        schema: Optional[str] = None,
    ) -> CommentOnExpression:
        """Build a standalone ``COMMENT ON`` expression.

        Args:
            object_type: Object kind enum or dialect-accepted object-kind
                string.  The default targets the source table.
            object_name: Object name, such as the source table or a dotted
                column reference.  Defaults to the source table name.
            comment: Comment text.  ``None`` represents the clear-comment
                form, subject to the backend formatter's grammar.
            schema: Optional schema qualifier.  Defaults to the source schema.

        Returns:
            A dialect-bound ``CommentOnExpression`` carrying the object kind,
            name, comment, and schema context.

        Raises:
            ValueError: If the resolved object name is empty or whitespace
                only, as rejected by the expression constructor.

        Notes:
            Standalone comments are distinct from inline column/table comment
            clauses.  Support for the object kind and comment form is checked
            by the dialect when the expression is rendered.
        """
        return CommentOnExpression(
            self.dialect,
            object_type=object_type,
            object_name=self.source.table_name() if object_name is None else object_name,
            comment=comment,
            schema=self.source.schema_name() if schema is None else schema,
        )

    def create_view(
        self,
        view_name: str,
        query: "QueryExpression",
        *,
        column_aliases: Optional[Sequence[Union[str, "ColumnAlias"]]] = None,
        replace: bool = False,
        temporary: bool = False,
        if_not_exists: bool = False,
        options: Optional["ViewOptions"] = None,
    ) -> CreateViewExpression:
        """Build a ``CREATE VIEW`` expression.

        Args:
            view_name: Name of the view to create.
            query: Query expression supplying the view definition.
            column_aliases: Optional output column names or ``ColumnAlias``
                declarations.
            replace: Request ``CREATE OR REPLACE`` semantics.
            temporary: Request a temporary view where supported.
            if_not_exists: Add the ``IF NOT EXISTS`` qualifier.
            options: Optional backend-specific ``ViewOptions`` declaration.

        Returns:
            A dialect-bound ``CreateViewExpression`` carrying the view name,
            query, aliases, flags, and options.

        Notes:
            The query is supplied as an expression; this method does not
            execute it.  View-option and qualifier support is evaluated by
            the backend formatter during rendering.
        """
        return CreateViewExpression(
            self.dialect,
            view_name=view_name,
            query=query,
            column_aliases=list(column_aliases) if column_aliases is not None else None,
            replace=replace,
            temporary=temporary,
            if_not_exists=if_not_exists,
            options=options,
        )

    def drop_view(
        self,
        view_name: str,
        *,
        if_exists: bool = False,
        cascade: bool = False,
    ) -> DropViewExpression:
        """Build a ``DROP VIEW`` expression.

        Args:
            view_name: Name of the view to remove.
            if_exists: Add the ``IF EXISTS`` qualifier.
            cascade: Request removal of dependent objects where supported.

        Returns:
            A dialect-bound ``DropViewExpression`` carrying the view name and
            requested flags.

        Notes:
            ``IF EXISTS`` and ``CASCADE`` are dialect capability options and
            are reported by the backend formatter when unsupported.
        """
        return DropViewExpression(
            self.dialect,
            view_name=view_name,
            if_exists=if_exists,
            cascade=cascade,
        )


class ActiveDDL(_ActiveDDLCore):
    """Synchronous source-bound DDL expression factory.

    The class exposes the inherited ``create_table``, index, view, comment,
    alter, drop, truncate, and ``partition_lifecycle`` factories.  It is
    synchronous only in the sense that it accepts a synchronous storage
    backend; all methods still return expression objects and never execute
    database operations.
    """


class AsyncActiveDDL(_ActiveDDLCore):
    """Asynchronous-backend source-bound DDL expression factory.

    This class has the same method names and return types as
    :class:`ActiveDDL` and accepts an asynchronous storage backend for API
    parity.  The methods are generation helpers, not coroutines: they do not
    await backend operations and do not execute DDL.
    """


__all__ = ["ActiveDDL", "AsyncActiveDDL"]
