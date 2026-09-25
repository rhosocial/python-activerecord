# src/rhosocial/activerecord/ddl/deriver.py
"""Derive concrete, dialect-bound DDL expressions from source declarations.

:class:`TableDDLDeriver` is the generation boundary between a structural
:class:`~rhosocial.activerecord.base.ddl.DDLSource` and the backend expression
classes.  It collects physical fields and table declarations, selects applicable
candidates, resolves column types, and constructs statement expressions using
the active dialect's preferred statement classes.

The deriver does not render final SQL, execute statements, create plans, or
contain backend compatibility fallbacks.  It may call a declaration's
``to_sql()`` indirectly through the selector as a renderability probe, but the
resulting SQL is discarded.  Backend formatters remain responsible for final
SQL and for capability errors tied to individual clauses.
"""

from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union, cast, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.core import TableExpression
from rhosocial.activerecord.backend.expression.statements.ddl_index import CreateIndexExpression, DropIndexExpression
from rhosocial.activerecord.backend.expression.statements.ddl_partition import PartitionClause
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnCommentClause,
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
    CreateTableOptions,
    DropTableExpression,
    GeneratedColumnExpression,
    IndexDefinition,
    StorageOptionsExpression,
    TableConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_truncate import TruncateExpression
from rhosocial.activerecord.backend.expression.types import DataType
from rhosocial.activerecord.base.ddl import ColumnAttribute, ColumnOptions, DDLSource as _DDLSource
from rhosocial.activerecord.base.fields import UseSqlType
from .selector import DeclarationSelectionError, DialectExpressionSelector, ExpressionOwnership
from .types import ColumnTypeResolutionError, ColumnTypeResolver

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class StatementContractError(TypeError):
    """Report a statement class that cannot accept canonical DDL parameters.

    This is a statement-family contract error, distinct from a source
    declaration type error.  A backend-specific statement subclass may add
    parameters, but it must still accept every canonical parameter collected
    for its statement family, either explicitly or through ``**kwargs``.
    """

    def __init__(self, statement: str, selected: Type[Any], missing: List[str]):
        """Initialize a statement parameter-contract error.

        Args:
            statement: Name of the canonical statement family, such as
                ``create_table`` or ``drop_table``.
            selected: The candidate statement class that was selected.
            missing: Collected parameter names absent from that class's
                keyword-capable constructor signature.

        Notes:
            ``missing`` is copied so the exception does not retain a mutable
            list owned by the caller.
        """
        self.statement = statement
        self.selected = selected
        self.missing = list(missing)
        super().__init__(
            f"{statement}: selected statement class {selected.__name__} does "
            f"not accept the canonical parameter(s) {missing}. A backend "
            f"subclass must accept every canonical parameter of its statement "
            f"family (forwarding super().__init__) and may add its own extras."
        )


class StatementParamSchema:
    """Inspect and instantiate statement constructors by parameter contract.

    The schema caches each class's ``__init__`` signature.  It treats
    ``dialect`` as the conventional first constructor argument and therefore
    excludes ``self`` and ``dialect`` from the canonical parameter map.  The
    canonical parameter values are supplied as keyword arguments, allowing a
    backend statement subclass to add its own optional parameters without
    changing the core collection code.
    """

    def __init__(self, base_class: Type[Any]):
        """Create a schema for one canonical statement family.

        Args:
            base_class: The generic expression class whose family name is
                reported when a selected subclass violates the contract.
        """
        self.base_class = base_class
        self._cache: Dict[Type[Any], Dict[str, inspect.Parameter]] = {}

    def parameters(self, cls: Type[Any]) -> Dict[str, inspect.Parameter]:
        """Return the canonical keyword parameters accepted by ``cls``.

        Args:
            cls: Statement class whose ``__init__`` signature is inspected.

        Returns:
            An insertion-ordered mapping of parameter names to
            :class:`inspect.Parameter` objects, excluding ``self`` and the
            conventional ``dialect`` argument.  The mapping is cached per
            class.

        Notes:
            The result includes variadic parameters when present; callers
            use a ``**kwargs`` parameter to permit otherwise unknown keys.
        """
        cached = self._cache.get(cls)
        if cached is None:
            signature = inspect.signature(cls.__init__)
            cached = {
                name: parameter
                for name, parameter in signature.parameters.items()
                if name not in ("self", "dialect")
            }
            self._cache[cls] = cached
        return cached

    def missing_params(self, cls: Type[Any], collected: Dict[str, Any]) -> List[str]:
        """Return collected names that a statement class cannot accept.

        Args:
            cls: Candidate statement class to inspect.
            collected: Canonical parameter values keyed by parameter name.

        Returns:
            Names present in ``collected`` but absent from ``cls``'s
            constructor parameters.  The result is empty when ``cls`` accepts
            ``**kwargs``.

        Notes:
            This check detects extra canonical parameters rejected by a narrow
            subclass.  It does not check whether a required constructor
            parameter is absent from ``collected``; the eventual constructor
            call reports that condition.
        """
        parameters = self.parameters(cls)
        var_keyword = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
        )
        return [name for name in collected if name not in parameters and not var_keyword]

    def defaults(self, cls: Type[Any]) -> Dict[str, Any]:
        """Return usable keyword defaults for a statement constructor.

        Args:
            cls: Statement class whose ``__init__`` signature is inspected.

        Returns:
            A mapping of parameter names to defaults for positional-or-keyword
            and keyword-only parameters that declare defaults.  Parameters
            without defaults, positional-only parameters, and variadic
            parameters are omitted.
        """
        return {
            name: parameter.default
            for name, parameter in self.parameters(cls).items()
            if parameter.default is not inspect.Parameter.empty
            and parameter.kind
            in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        }

    def instantiate(self, cls: Type[Any], dialect: Any, collected: Dict[str, Any]) -> Any:
        """Instantiate a statement class with canonical parameters.

        Args:
            cls: Selected statement class to construct.
            dialect: Dialect passed as the conventional first constructor
                argument.
            collected: Canonical parameter values keyed by name; these values
                override the class's declared defaults.

        Returns:
            A newly constructed statement expression of ``cls`` (or a backend
            subclass).

        Raises:
            StatementContractError: If ``cls`` cannot accept one or more
                collected parameter names and has no ``**kwargs`` escape
                hatch.
            TypeError: Propagated by the selected constructor for invalid or
                missing required parameters.

        Notes:
            The call is keyword-based after ``dialect``.  A backend subclass
            may add optional keyword parameters, but it must preserve the
            canonical family parameters.
        """
        missing = self.missing_params(cls, collected)
        if missing:
            raise StatementContractError(self.base_class.__name__, cls, missing)
        params = self.defaults(cls)
        params.update(collected)
        return cls(dialect, **params)


class TableDDLDeriver:
    """Derive table and related DDL expressions from one source/dialect pair.

    The deriver caches source primary-key metadata and the dialect's inline
    index capability at construction time.  It exposes separate methods for
    collecting source declarations and for constructing CREATE/DROP table,
    index, and truncate statement expressions.  All methods are synchronous
    and generation-only.
    """

    def __init__(self, source: _DDLSource, dialect: "SQLDialectBase"):
        """Create a deriver for a structural source and active dialect.

        Args:
            source: Object implementing the DDL declaration protocol.
            dialect: SQL dialect used to bind and select declarations.

        Notes:
            The constructor reads primary-key metadata and calls
            ``dialect.supports_inline_index()``.  It does not render or
            execute a statement.
        """
        self.source = source
        self.dialect = dialect
        self.type_resolver = ColumnTypeResolver(dialect)
        self.selector = DialectExpressionSelector(dialect)
        self.pk_columns = tuple(source.primary_key_columns())
        self.composite_pk = source.is_composite_pk()
        self._inline_capable = bool(cast(Any, dialect).supports_inline_index())

    def _statement_candidates(
        self,
        preferred: Optional[Type[BaseExpression]],
        generic: Type[BaseExpression],
    ) -> List[Type[BaseExpression]]:
        """Build an ordered, duplicate-free statement candidate list.

        Args:
            preferred: Optional backend-preferred statement class.
            generic: Generic statement class used as the fallback.

        Returns:
            ``[preferred, generic]`` when a preferred class exists, otherwise
            ``[generic]``; duplicate class objects are removed while
            preserving order.
        """
        candidates: List[Type[BaseExpression]] = []
        for candidate in ([preferred] if preferred is not None else []) + [generic]:
            if candidate not in candidates:
                candidates.append(candidate)
        return candidates

    def _statement_renderable(self, cls: Type[BaseExpression]) -> bool:
        """Return whether a statement class exposes a dialect format method.

        Args:
            cls: Candidate statement class to inspect.

        Returns:
            ``True`` when its ``format_method`` property can be read and the
            active dialect has an attribute with the returned name;
            otherwise ``False``.

        Notes:
            Property access is performed without constructing ``cls``.  Errors
            raised while reading a custom property are treated as
            non-renderability rather than propagated.
        """
        prop = getattr(cls, "format_method", None)
        function_getter = getattr(prop, "fget", None)
        if function_getter is None:
            return False
        try:
            method_name = function_getter(None)
        except Exception:
            return False
        return hasattr(self.dialect, method_name)

    def select_statement_class(
        self,
        candidates: List[Type[BaseExpression]],
        statement: str,
    ) -> Type[BaseExpression]:
        """Select the first statement class owned and renderable here.

        Args:
            candidates: Ordered statement classes to inspect.
            statement: Statement interface name used in selection errors.

        Returns:
            The first candidate classified as generic or owned by this
            dialect and exposing a formatting method on it.

        Raises:
            DeclarationSelectionError: If every candidate is foreign or has no
                dialect rendering method.

        Notes:
            Candidate classes are not instantiated here.  Their constructor
            contract is checked later by :class:`StatementParamSchema`.
        """
        failures: List[Tuple[str, str, str]] = []
        for candidate in candidates:
            owner_label = self.selector._owner_label(candidate)
            if self.selector.ownership.classify(candidate) == ExpressionOwnership.FOREIGN:
                failures.append(
                    (candidate.__name__, owner_label, "owned by a foreign backend")
                )
                continue
            if not self._statement_renderable(candidate):
                failures.append(
                    (
                        candidate.__name__,
                        owner_label,
                        "dialect provides no rendering method for it",
                    )
                )
                continue
            return candidate
        raise DeclarationSelectionError(statement, failures)

    def create_table(
        self,
        *,
        if_not_exists: bool = False,
        temporary: bool = False,
        inline_indexes: Optional[bool] = None,
    ) -> CreateTableExpression:
        """Build a source-derived ``CREATE TABLE`` expression.

        Args:
            if_not_exists: Add the ``IF NOT EXISTS`` flag to the expression.
            temporary: Add the ``TEMPORARY`` flag to the expression.
            inline_indexes: ``None`` uses the dialect capability detected at
                construction; ``True`` includes merged source indexes in the
                table expression; ``False`` leaves the inline list empty.

        Returns:
            A dialect-bound ``CreateTableExpression`` selected from the
            source override, backend-preferred class, or generic class.

        Raises:
            DeclarationSelectionError: If source declarations or statement
                candidates have no applicable dialect form.
            ValueError: If inline indexes contain statement-level options that
                cannot be represented inside ``CREATE TABLE``.
            StatementContractError: If the selected statement class rejects
                the canonical CREATE TABLE parameters.

        Notes:
            The expression carries canonical source-derived values only.  SQL
            option capability checks and final formatting remain in the
            selected backend statement formatter.
        """
        if inline_indexes is None:
            inline = self._inline_capable
        else:
            inline = bool(inline_indexes)
        indexes = self.indexes() if inline else []
        if inline:
            self._gate_inline_statement_options(indexes)
        params: Dict[str, Any] = {
            "table": self.table_expression(),
            "columns": self.columns(),
            "indexes": indexes,
            "table_constraints": self.table_constraints(),
            "table_options": self.table_options(),
            "storage_options": self.storage_options(),
            "partition": self.partition(),
            "temporary": temporary,
            "if_not_exists": if_not_exists,
            "inherits": self.source.table_inherits(),
            "tablespace": self.source.table_tablespace(),
        }
        override = self.source.create_table_statement_classes()
        candidates = (
            self._statement_candidates(
                getattr(self.dialect, "preferred_create_table_statement", lambda: None)(),
                CreateTableExpression,
            )
            if override is None
            else self._normalized_classes(override)
        )
        schema = StatementParamSchema(CreateTableExpression)
        selected = self.select_statement_class(candidates, "create_table")
        return schema.instantiate(selected, self.dialect, params)

    def _normalized_classes(
        self,
        override: Union[Type[BaseExpression], Sequence[Type[BaseExpression]]],
    ) -> List[Type[BaseExpression]]:
        """Normalize a source statement-class override to a candidate list.

        Args:
            override: One statement class or a list/tuple of classes returned
                by the source.

        Returns:
            A list containing the single class or a shallow copy of the
            sequence.

        Notes:
            Type validation is deferred to statement selection and
            instantiation; this helper only normalizes the container shape.
        """
        if isinstance(override, (list, tuple)):
            normalized = cast(Sequence[Type[BaseExpression]], override)
            return list(normalized)
        return [cast(Type[BaseExpression], override)]

    def _gate_inline_statement_options(self, indexes: List[IndexDefinition]) -> None:
        """Reject index options that cannot be embedded in ``CREATE TABLE``.

        Args:
            indexes: Merged index declarations considered for the inline path.

        Returns:
            ``None`` when every index is safe to inline.

        Raises:
            ValueError: If any index declares ``if_not_exists``, ``tablespace``,
                or ``concurrent``.  These options belong to standalone CREATE
                INDEX statements and cannot be carried by the inline form.

        Notes:
            The check is intentionally performed before statement selection so
            the error identifies the declaration and suggests the standalone
            index path.
        """
        offenders: List[Tuple[str, List[str]]] = []
        for index in indexes:
            declared: List[str] = []
            if index.if_not_exists:
                declared.append("if_not_exists")
            if index.tablespace is not None:
                declared.append("tablespace")
            if index.concurrent:
                declared.append("concurrent")
            if declared:
                offenders.append((index.name, declared))
        if offenders:
            details = "; ".join(
                f"{name!r}: {', '.join(options)}" for name, options in offenders
            )
            raise ValueError(
                "create_table(): the inline index path cannot carry "
                f"statement-level options ({details}). Use "
                "create_table(inline_indexes=False) with create_indexes() / "
                "drop_indexes() to emit standalone statements per index."
            )

    def create_indexes(self) -> List[CreateIndexExpression]:
        """Build standalone ``CREATE INDEX`` expressions when required.

        Returns:
            An empty list when the dialect supports inline indexes, because
            those declarations are carried by :meth:`create_table`.  Otherwise
            one dialect-bound ``CreateIndexExpression`` is returned for each
            merged, applicable index declaration in source order.

        Raises:
            DeclarationSelectionError: If an index declaration or statement
                candidate is not applicable to the active dialect.
            StatementContractError: If the selected statement class rejects the
                canonical CREATE INDEX parameters.

        Notes:
            ``if_not_exists``, index type, partial predicates, include columns,
            tablespaces, and concurrent creation are carried from each
            declaration.  Their dialect capability checks occur when the
            returned expression is rendered.
        """
        if self._inline_capable:
            return []
        schema = StatementParamSchema(CreateIndexExpression)
        candidates = self._statement_candidates(
            getattr(self.dialect, "preferred_create_index_statement", lambda: None)(),
            CreateIndexExpression,
        )
        selected = self.select_statement_class(candidates, "create_indexes")
        return [
            schema.instantiate(
                selected,
                self.dialect,
                {
                    "table_name": self.source.table_name(),
                    "index_name": index.name,
                    "columns": list(index.columns),
                    "unique": index.unique,
                    "index_type": index.type,
                    "where": index.partial_condition,
                    "include": list(index.include_columns) if index.include_columns else None,
                    "if_not_exists": bool(index.if_not_exists),
                    "tablespace": index.tablespace,
                    "concurrent": bool(index.concurrent),
                },
            )
            for index in self.indexes()
        ]

    def drop_indexes(self, *, if_exists: bool = False) -> List[DropIndexExpression]:
        """Build one ``DROP INDEX`` expression for every declared index.

        Args:
            if_exists: Fallback value used when an individual index
                declaration leaves ``if_exists`` unspecified.

        Returns:
            A list of dialect-bound ``DropIndexExpression`` objects in merged
            declaration order.  Each declaration's ``if_exists`` value wins
            when it is not ``None``; otherwise the method-level fallback is
            used, and each declaration's ``concurrent`` value is carried
            through.

        Raises:
            DeclarationSelectionError: If the source index declaration or
                selected statement class is not applicable to the dialect.
            StatementContractError: If the selected statement class rejects the
                canonical DROP INDEX parameters.

        Notes:
            The returned expressions are independent of CREATE INDEX
            generation and are not executed by this method.  ``ON <table>``
            syntax and other vendor options remain dialect formatting concerns.
        """
        schema = StatementParamSchema(DropIndexExpression)
        candidates = self._statement_candidates(
            getattr(self.dialect, "preferred_drop_index_statement", lambda: None)(),
            DropIndexExpression,
        )
        selected = self.select_statement_class(candidates, "drop_indexes")
        return [
            schema.instantiate(
                selected,
                self.dialect,
                {
                    "index_name": index.name,
                    "table_name": self.source.table_name(),
                    "if_exists": (
                        index.if_exists if index.if_exists is not None else if_exists
                    ),
                    "concurrent": bool(index.concurrent),
                },
            )
            for index in self.indexes()
        ]

    def drop_table(
        self,
        *,
        if_exists: bool = False,
        cascade: Optional[bool] = None,
        purge: bool = False,
    ) -> DropTableExpression:
        """Build a source-derived ``DROP TABLE`` expression.

        Args:
            if_exists: Add the ``IF EXISTS`` flag.
            cascade: ``None`` omits an explicit dependency policy, ``True``
                requests cascade behavior, and ``False`` requests restrict
                behavior.
            purge: Add a backend-specific purge flag.

        Returns:
            A dialect-bound ``DropTableExpression`` using the selected backend
            statement class when one is preferred.

        Raises:
            DeclarationSelectionError: If no preferred or generic DROP TABLE
                class is owned and renderable by the dialect.
            StatementContractError: If the selected class rejects the canonical
                DROP TABLE parameters.

        Notes:
            The expression carries the requested flags; the dialect formatter
            decides whether each flag is supported and raises
            ``UnsupportedFeatureError`` during rendering when it is not.
        """
        schema = StatementParamSchema(DropTableExpression)
        candidates = self._statement_candidates(
            getattr(self.dialect, "preferred_drop_table_statement", lambda: None)(),
            DropTableExpression,
        )
        selected = self.select_statement_class(candidates, "drop_table")
        return schema.instantiate(
            selected,
            self.dialect,
            {
                "table": self.table_expression(),
                "if_exists": if_exists,
                "cascade": cascade,
                "purge": purge,
            },
        )

    def table_expression(self) -> TableExpression:
        """Return the source table as a dialect-bound table reference.

        Returns:
            A ``TableExpression`` containing ``source.table_name()`` and the
            optional ``source.schema_name()``.

        Notes:
            This helper creates a reference node only; it does not render the
            identifier or check table-level feature capabilities.
        """
        return TableExpression(
            self.dialect,
            self.source.table_name(),
            schema_name=self.source.schema_name(),
        )

    def truncate(
        self,
        *,
        restart_identity: bool = False,
        cascade: bool = False,
    ) -> TruncateExpression:
        """Build a source-derived ``TRUNCATE TABLE`` expression.

        Args:
            restart_identity: Request identity-counter reset where the
                dialect supports it.
            cascade: Request truncation of dependent objects where supported.

        Returns:
            A dialect-bound ``TruncateExpression`` selected from the backend
            preferred class or the generic class.

        Raises:
            DeclarationSelectionError: If no preferred or generic statement
                class is owned and renderable by the dialect.
            StatementContractError: If the selected class rejects the canonical
                TRUNCATE parameters.

        Notes:
            Option support is checked by the dialect formatter when the
            returned expression is rendered; this method only constructs the
            statement node.
        """
        schema = StatementParamSchema(TruncateExpression)
        candidates = self._statement_candidates(
            getattr(self.dialect, "preferred_truncate_statement", lambda: None)(),
            TruncateExpression,
        )
        selected = self.select_statement_class(candidates, "truncate")
        return schema.instantiate(
            selected,
            self.dialect,
            {
                "table_name": self.source.table_name(),
                "restart_identity": restart_identity,
                "cascade": cascade,
            },
        )

    def indexes(self) -> List[IndexDefinition]:
        """Collect, merge, deduplicate, and select index declarations.

        Returns:
            A list of dialect-bound ``IndexDefinition`` objects.  Field-level
            indexes are visited first in ``source.ddl_field_names()`` order,
            followed by table-level indexes.  The first declaration for a
            given name wins, so a table-level duplicate does not replace an
            earlier field-level declaration.

        Raises:
            DeclarationSelectionError: If an additive generic or owned
                declaration cannot be rendered by the active dialect.

        Notes:
            Derived fields are skipped.  Foreign-backend alternatives are
            omitted for this additive declaration, while unsupported
            generic/owned alternatives fail rather than being silently lost.
        """
        merged: Dict[str, IndexDefinition] = {}
        for field in self.source.ddl_field_names():
            if self.source.is_derived_field(field):
                continue
            for index in self.source.column_indexes(field):
                merged.setdefault(index.name, index)
        for index in self.source.table_indexes():
            merged.setdefault(index.name, index)
        return self.selector.select_many(
            "table_indexes",
            list(merged.values()),
            IndexDefinition,
        )

    def table_constraints(self) -> List[TableConstraint]:
        """Collect and select table-level constraint declarations.

        Returns:
            A list of dialect-bound ``TableConstraint`` objects in source
            declaration order.

        Raises:
            DeclarationSelectionError: If a generic or active-backend table
                constraint cannot be rendered by the active dialect.

        Notes:
            This is an additive declaration: foreign-backend alternatives are
            skipped, while a present but inapplicable generic/owned
            declaration is an error.
        """
        return self.selector.select_many(
            "table_constraints",
            self.source.table_constraints(),
            TableConstraint,
        )

    def table_options(self) -> Optional[CreateTableOptions]:
        """Select the first applicable table-options declaration.

        Returns:
            A dialect-bound ``CreateTableOptions`` expression, or ``None`` when
            the source declares no table options.

        Raises:
            DeclarationSelectionError: If declared table options have no
                applicable candidate for the active dialect.

        Notes:
            This is a single-choice declaration.  A list/tuple is considered
            in declaration order, and the first applicable option wins.
        """
        return self.selector.select_one(
            "table_options",
            self.source.table_options(),
            CreateTableOptions,
        )

    def storage_options(self) -> Optional[StorageOptionsExpression]:
        """Select the first applicable storage-options declaration.

        Returns:
            A dialect-bound ``StorageOptionsExpression`` expression, or
            ``None`` when the source declares no storage options.

        Raises:
            DeclarationSelectionError: If declared storage options have no
                applicable candidate for the active dialect.

        Notes:
            The generic storage-options expression contains a developer-
            supplied option mapping.  Literal formatting and backend-specific
            storage syntax remain dialect responsibilities.
        """
        return self.selector.select_one(
            "table_storage_options",
            self.source.table_storage_options(),
            StorageOptionsExpression,
        )

    def partition(self) -> Optional[PartitionClause]:
        """Select the first applicable table-partition declaration.

        Returns:
            A dialect-bound ``PartitionClause`` expression, or ``None`` when
            the source declares no partitioning clause.

        Raises:
            DeclarationSelectionError: If the declared partition clause is
                foreign to the active backend or cannot be rendered by it.

        Notes:
            The core declaration carries the generic ``PARTITION BY`` clause
            shape.  Concrete partition boundaries and backend-specific
            partition forms remain in backend expression subclasses.
        """
        return self.selector.select_one(
            "table_partition",
            self.source.table_partition(),
            PartitionClause,
        )

    def columns(self) -> List[ColumnDefinition]:
        """Build every physical column definition in source order.

        Returns:
            A list of ``ColumnDefinition`` objects, excluding fields marked as
            derived by the source.

        Raises:
            ColumnTypeResolutionError: If a field's Python type cannot be
                resolved to a supported dialect type.
            DeclarationSelectionError: If a column declaration, attribute, or
                generated-column candidate is not applicable.
            TypeError: If a source column name or selected column class fails
                its constructor contract.
        """
        return [
            self.column_definition(field)
            for field in self.source.ddl_field_names()
            if not self.source.is_derived_field(field)
        ]

    def column_definition(self, field: str) -> ColumnDefinition:
        """Assemble one physical column definition from source declarations.

        Args:
            field: Source field name whose database column should be built.

        Returns:
            A dialect-bound ``ColumnDefinition`` or a backend-specific
            ``ColumnDefinition`` subclass selected by the field's
            ``ColumnOptions``.

        Raises:
            ColumnTypeResolutionError: If the field type cannot be resolved.
            DeclarationSelectionError: If constraints, column options,
                comments, or generated-column candidates have no applicable
                dialect form.
            TypeError: If the source column name is not a string or a selected
                column class rejects the assembled parameters.

        Notes:
            The assembly order is type resolution, constraint and attribute
            selection, identity nullability normalization, column-option
            selection, then construction.  A selected ``ColumnOptions``
            instance can choose a custom column class and apply backend-
            specific fields after construction.  Unsupported comment or
            generated-column rendering can still be reported later by the
            backend formatter.
        """
        data_type = self.resolve_type(field)
        constraints = self.column_constraints(field, data_type)
        attributes = self.selected_column_attributes(field)
        constraints = self._apply_identity_nullability(field, constraints, attributes)
        options: Optional[ColumnOptions] = self.selector.select_one(
            "column_options",
            self.source.column_options(field),
            ColumnOptions,
        )
        column_class = (
            options.column_definition_class() if options is not None else ColumnDefinition
        )
        name = self.source.column_name(field)
        self.selector.validate(name, "column_name", str)
        comment_text = self.selector.select_one(
            "column_comment",
            self.source.column_comment(field),
            str,
        )
        column = column_class(
            self.dialect,
            name,
            data_type,
            constraints=constraints,
            comment=(
                ColumnCommentClause(self.dialect, comment_text)
                if comment_text is not None
                else None
            ),
            generated_expression=self.selector.select_one(
                "generated_column",
                self.source.generated_column(field),
                GeneratedColumnExpression,
            ),
            attributes=attributes,
        )
        if options is not None:
            options.apply_to(column)
        return column

    def selected_column_attributes(self, field: str) -> List[ColumnAttribute]:
        """Return the active dialect's selected column attributes.

        Args:
            field: Source field whose declared attributes should be filtered.

        Returns:
            A list containing the attributes accepted by
            ``dialect.select_column_attributes()``; an empty list is returned
            without calling the dialect when the source declares none.

        Raises:
            DeclarationSelectionError: Propagated when the dialect cannot
                render an unknown generic attribute.

        Notes:
            Foreign-backend attributes and known attributes unsupported by the
            active dialect are skipped by the dialect selector.  The returned
            attributes are dialect-free declarations and are not rebound by
            this method.
        """
        attributes = self.source.column_attributes(field)
        if not attributes:
            return []
        return cast(Any, self.dialect).select_column_attributes(attributes)

    def _apply_identity_nullability(
        self,
        field: str,
        constraints: List[ColumnConstraint],
        attributes: List[ColumnAttribute],
    ) -> List[ColumnConstraint]:
        """Normalize nullability constraints for an identity column.

        Args:
            field: Source field name; the current normalization logic does
                not inspect this value.
            constraints: Selected column constraints in declaration order.
            attributes: Selected column attributes checked for ``kind ==
                "identity"``.

        Returns:
            The original constraint list when no identity attribute is
            present; otherwise a new list with all ``NULL`` constraints
            removed and at least one ``NOT NULL`` constraint present.

        Notes:
            Existing ``NOT NULL`` constraints are preserved and the helper
            appends one only when none is declared.  It does not add a primary
            key or otherwise change the source's constraint semantics.
        """
        if not any(getattr(attribute, "kind", "") == "identity" for attribute in attributes):
            return constraints
        constraints = [
            constraint
            for constraint in constraints
            if constraint.constraint_type != ColumnConstraintType.NULL
        ]
        declared_types = {constraint.constraint_type for constraint in constraints}
        if ColumnConstraintType.NOT_NULL not in declared_types:
            constraints.append(ColumnConstraint(self.dialect, ColumnConstraintType.NOT_NULL))
        return constraints

    def resolve_type(self, field: str) -> DataType:
        """Resolve one source field to a supported dialect data type.

        Args:
            field: Source field name whose Python type and optional type
                declaration should be resolved.

        Returns:
            A dialect-bound ``DataType`` expression selected by
            :class:`~rhosocial.activerecord.ddl.types.ColumnTypeResolver`.

        Raises:
            ColumnTypeResolutionError: If no declared, inferred, or suggested
                type is supported.  The error is re-raised with the field name
                for source-level context.
        """
        python_type = self.source.field_python_type(field)
        declared = self.source.column_type(field)
        try:
            if declared is None:
                return self.type_resolver.resolve(python_type)
            if isinstance(declared, UseSqlType):
                return self.type_resolver.resolve(python_type, declared)
            if isinstance(declared, DataType):
                return self.type_resolver.resolve_candidates(python_type, [declared])
            return self.type_resolver.resolve_candidates(python_type, list(declared))
        except ColumnTypeResolutionError as exc:
            raise ColumnTypeResolutionError(f"Field {field!r}: {exc}") from exc

    def column_constraints(
        self,
        field: str,
        data_type: DataType,
    ) -> List[ColumnConstraint]:
        """Select and adjust one field's column constraints.

        Args:
            field: Source field whose declared constraints should be selected.
            data_type: Already-resolved type used to decide whether an integer
                primary key can be marked auto-incrementing.

        Returns:
            A list of dialect-bound ``ColumnConstraint`` objects in declaration
            order.  For a single-column primary key backed by an integer type,
            a dialect advertising ``supports_auto_increment()`` may cause the
            primary-key constraint's ``is_auto_increment`` flag to be set.

        Raises:
            DeclarationSelectionError: If a generic or active-backend constraint
                cannot be rendered by the active dialect.
        """
        constraints = self.selector.select_many(
            "column_constraints",
            self.source.column_constraints(field),
            ColumnConstraint,
        )
        if not self.composite_pk and self.source.column_name(field) in self.pk_columns:
            support = getattr(self.dialect, "supports_auto_increment", None)
            if self.type_resolver.is_integer(data_type) and support is not None and support():
                for constraint in constraints:
                    if constraint.constraint_type == ColumnConstraintType.PRIMARY_KEY:
                        constraint.is_auto_increment = True
        return constraints


__all__ = [
    "StatementContractError",
    "StatementParamSchema",
    "TableDDLDeriver",
]
