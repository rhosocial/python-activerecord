# src/rhosocial/activerecord/backend/expression/statements/ddl_table.py
"""Table DDL statement expressions and related types."""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

from ..bases import BaseExpression, SQLPredicate, SQLQueryAndParams
from ..core import TableExpression
from ..types import DataType

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from .dql import QueryExpression


class ColumnConstraintType(Enum):
    """Types of column constraints."""

    PRIMARY_KEY = "PRIMARY KEY"
    NOT_NULL = "NOT NULL"
    NULL = "NULL"  # Explicitly allow NULL (usually redundant but sometimes needed for clarity)
    UNIQUE = "UNIQUE"
    CHECK = "CHECK"
    FOREIGN_KEY = "FOREIGN KEY"
    DEFAULT = "DEFAULT"


class ColumnConstraint(BaseExpression):
    """Represents a column constraint clause (PRIMARY KEY, NOT NULL, UNIQUE, …).

    A DDL clause node: it participates in rendering through the dialect's
    ``format_column_constraint`` and holds the expressions its grammar
    contains (CHECK condition, DEFAULT value).
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_constraint"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        constraint_type: ColumnConstraintType,
        name: Optional[str] = None,
        check_condition: Optional["SQLPredicate"] = None,
        foreign_key_reference: Optional[Tuple[str, List[str]]] = None,
        default_value: Any = None,
        is_auto_increment: bool = False,
        on_delete: Optional["ReferentialAction"] = None,
        on_update: Optional["ReferentialAction"] = None,
        deferrable: Optional[bool] = None,
        initially_deferred: Optional[bool] = None,
        enforced: Optional[bool] = None,
    ):
        super().__init__(dialect)
        self.constraint_type = constraint_type
        self.name = name
        self.check_condition = check_condition
        self.foreign_key_reference = foreign_key_reference
        self.default_value = default_value
        self.is_auto_increment = is_auto_increment
        self.on_delete = on_delete
        self.on_update = on_update
        self.deferrable = deferrable
        self.initially_deferred = initially_deferred
        self.enforced = enforced


class DefaultValueClause(BaseExpression):
    """The value clause of a ``DEFAULT`` constraint.

    A DDL clause node rendered through the dialect's
    ``format_default_value_clause``. It carries the default **value** — either
    a plain Python scalar (rendered inline with dialect-controlled escaping) or
    a ``BaseExpression`` (e.g. a function call or literal) — keeping the
    value/inline logic in one place. It is a self-contained expression so the
    value's escaping/inlining can be overridden per backend.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_default_value_clause"

    def __init__(self, dialect: "SQLDialectBase", value: Any):
        super().__init__(dialect)
        self.value = value


class IdentityClause(BaseExpression):
    """The identity/auto-increment clause of a column definition.

    A DDL clause node rendered through the dialect's ``format_identity_clause``.
    It carries the identity **parameters** (generation, start, increment,
    bounds, cycle) so the syntax differences between backends live in one
    place: MySQL/MariaDB ``AUTO_INCREMENT``, SQL Server ``IDENTITY(seed, inc)``,
    PostgreSQL/Oracle/Firebird ``GENERATED {ALWAYS|BY DEFAULT} AS IDENTITY
    (START WITH ... INCREMENT BY ...)``, SQLite ``AUTOINCREMENT``.

    ``generation`` is ``"ALWAYS"`` or ``"BY DEFAULT"`` (``None`` defaults to
    ``BY DEFAULT``); ``start``/``increment``/``minvalue``/``maxvalue``/``cycle``
    are optional sequence attributes.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_identity_clause"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        generation: Optional[str] = None,
        *,
        start: Optional[int] = None,
        increment: Optional[int] = None,
        minvalue: Optional[int] = None,
        maxvalue: Optional[int] = None,
        cycle: Optional[bool] = None,
    ):
        super().__init__(dialect)
        self.generation = generation
        self.start = start
        self.increment = increment
        self.minvalue = minvalue
        self.maxvalue = maxvalue
        self.cycle = cycle


class ReferencesClause(BaseExpression):
    """The ``REFERENCES`` clause of a foreign key.

    A DDL clause node rendered through the dialect's ``format_references_clause``.
    Shared by column-level (``ColumnConstraint``) and table-level
    (``ForeignKeyConstraint``) foreign keys so the reference syntax lives in one
    place: the referenced table/columns plus the referential actions
    (``MATCH`` / ``ON DELETE`` / ``ON UPDATE``) and deferrability.

    ``ReferentialAction`` values are resolved by the dialect's
    ``format_references_clause``; ``on_delete``/``on_update`` are accepted as
    the enum or its string value.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_references_clause"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        referenced_table: str,
        referenced_columns: List[str],
        *,
        on_delete: Optional["ReferentialAction"] = None,
        on_update: Optional["ReferentialAction"] = None,
        match_type: Optional[str] = None,
        deferrable: Optional[bool] = None,
        initially_deferred: Optional[bool] = None,
    ):
        super().__init__(dialect)
        self.referenced_table = referenced_table
        self.referenced_columns = list(referenced_columns or [])
        self.on_delete = on_delete
        self.on_update = on_update
        self.match_type = match_type
        self.deferrable = deferrable
        self.initially_deferred = initially_deferred


class GeneratedColumnType(Enum):
    """Types of generated columns (computed columns)."""

    STORED = "STORED"  # Stored on disk, can be indexed
    VIRTUAL = "VIRTUAL"  # Computed on read, not stored


class GeneratedColumnExpression(BaseExpression):
    """Represents the GENERATED ALWAYS AS (<expr>) [STORED|VIRTUAL] clause.

    A DDL clause node rendered through the dialect's
    ``format_generated_column_expression``.  Holds the inner expression
    (any ``BaseExpression``) and the storage type.

    Usage::

        gen = GeneratedColumnExpression(
            dialect,
            expression=Column(dialect, "price") * Column(dialect, "qty"),
            storage_type=GeneratedColumnType.STORED,
        )
        sql, params = gen.to_sql()
        # -> ('GENERATED ALWAYS AS ("price" * "qty") STORED', ())
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_generated_column_expression"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expression: "BaseExpression",
        storage_type: Optional[GeneratedColumnType] = None,
    ):
        super().__init__(dialect)
        self.expression = expression
        self.storage_type = storage_type or GeneratedColumnType.VIRTUAL


class ColumnCommentClause(BaseExpression):
    """The inline comment clause of a column definition.

    A CREATE TABLE / ALTER TABLE **clause** node rendered through the
    dialect's ``format_column_comment_clause``.  It is deliberately distinct
    from the standalone ``COMMENT ON`` statement (:class:`CommentOnExpression`):
    the inline clause is part of the *column-definition grammar* and only
    exists on dialects that advertise :meth:`supports_column_comment`.

    Dialects render it differently — MySQL/MariaDB/SQLite-family emit
    ``COMMENT '<text>'``, BigQuery emits ``OPTIONS(description='<text>')``;
    PostgreSQL/Oracle/Firebird/SQL Server have no inline column-comment
    grammar and raise ``UnsupportedFeatureError`` instead of silently
    dropping the declared comment.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_comment_clause"

    def __init__(self, dialect: "SQLDialectBase", comment: str):
        super().__init__(dialect)
        self.comment = comment


class TableCommentClause(BaseExpression):
    """The inline table-comment clause of ``CREATE TABLE``.

    A CREATE TABLE **clause** node rendered through the dialect's
    ``format_table_comment_clause``.  There is no SQL-standard table-comment
    mechanism: the bare ``COMMENT '<text>'`` table option is a
    MySQL/MariaDB/ClickHouse-family convenience (Snowflake renders
    ``COMMENT = '<text>'``, BigQuery ``OPTIONS(description='<text>')``), while
    the standalone ``COMMENT ON`` statement is a separate de-facto vendor
    mechanism (:class:`CommentOnExpression`), not this clause.

    Rendering is capability-gated: the statement renderer emits this clause
    only on dialects whose :meth:`supports_table_comment` is True, and raises
    ``UnsupportedFeatureError`` on the others instead of silently dropping a
    declared comment.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_comment_clause"

    def __init__(self, dialect: "SQLDialectBase", comment: str):
        super().__init__(dialect)
        self.comment = comment


class ColumnDefinition(BaseExpression):
    """Represents a column definition clause within CREATE/ALTER TABLE.

    A DDL clause node rendered through the dialect's
    ``format_column_definition``; its children (data type, constraints,
    generated-column expression, inline comment clause) are proper expression
    nodes, so dialect propagation reaches the whole clause subtree.

    ``comment`` is a :class:`ColumnCommentClause` (or ``None``); bare comment
    text is **not** accepted here — build the clause node explicitly so the
    inline comment always flows through the clause channel.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_definition"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        data_type: "DataType",
        constraints: Optional[List[ColumnConstraint]] = None,
        comment: Optional["ColumnCommentClause"] = None,
        generated_expression: Optional[GeneratedColumnExpression] = None,
        attributes: Optional[List[Any]] = None,
    ):
        super().__init__(dialect)
        if not isinstance(data_type, DataType):
            raise TypeError(
                f"data_type must be a DataType instance, got {type(data_type).__name__}"
            )
        if comment is not None and not isinstance(comment, ColumnCommentClause):
            raise TypeError(
                f"comment must be a ColumnCommentClause, got {type(comment).__name__}"
            )
        self.name = name
        self.data_type = data_type
        self.constraints = list(constraints or [])
        self.comment = comment
        self.generated_expression = generated_expression
        # Dialect-free column attributes (identity, collation, character set,
        # …) — already selected by the dialect's ``select_column_attributes``;
        # rendered through ``format_column_attribute``.
        self.attributes = list(attributes or [])


class TableConstraintType(Enum):
    """Types of table constraints supported by SQL."""

    PRIMARY_KEY = "PRIMARY KEY"
    UNIQUE = "UNIQUE"
    FOREIGN_KEY = "FOREIGN KEY"
    CHECK = "CHECK"
    EXCLUDE = "EXCLUDE"


class ReferentialAction(Enum):
    """Actions for referential integrity constraints."""

    CASCADE = "CASCADE"
    RESTRICT = "RESTRICT"
    SET_NULL = "SET NULL"
    SET_DEFAULT = "SET DEFAULT"
    NO_ACTION = "NO ACTION"


# Re-export partition clause from ddl_partition
from .ddl_partition import PartitionClause, PartitionStrategy  # noqa: E402, F401


class ConstraintValidation(Enum):
    """Constraint validation status (PostgreSQL specific).

    Used as the typed ``validation`` field of ``TableConstraint`` to control
    whether PostgreSQL validates existing data against the constraint.

    - VALIDATE: Validate all existing data (default behavior)
    - NOVALIDATE: Add constraint without validating existing data (NOT VALID)
    """

    VALIDATE = "VALIDATE"
    NOVALIDATE = "NOT VALID"


class TableConstraint(BaseExpression):
    """Represents a table-level constraint clause in CREATE/ALTER TABLE."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_constraint"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        constraint_type: TableConstraintType,
        name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        check_condition: Optional["SQLPredicate"] = None,
        foreign_key_table: Optional[str] = None,
        foreign_key_columns: Optional[List[str]] = None,
        deferrable: Optional[bool] = None,
        initially_deferred: Optional[bool] = None,
        validation: Optional[ConstraintValidation] = None,
        enforced: Optional[bool] = None,
    ):
        super().__init__(dialect)
        self.constraint_type = constraint_type
        self.name = name
        self.columns = columns
        self.check_condition = check_condition
        self.foreign_key_table = foreign_key_table
        self.foreign_key_columns = foreign_key_columns
        self.deferrable = deferrable
        self.initially_deferred = initially_deferred
        # PostgreSQL: NOT VALID for an added constraint (None = default VALIDATE).
        self.validation = validation
        # MariaDB/SQL Server: CHECK ... [NOT] ENFORCED (None = backend default).
        self.enforced = enforced


class ForeignKeyConstraint(TableConstraint):
    """Specialized table constraint for foreign keys with additional options."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_constraint"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        columns: Optional[List[str]] = None,
        foreign_key_table: Optional[str] = None,
        foreign_key_columns: Optional[List[str]] = None,
        on_delete: "ReferentialAction" = ReferentialAction.NO_ACTION,
        on_update: "ReferentialAction" = ReferentialAction.NO_ACTION,
        match_type: Optional[str] = None,
        name: Optional[str] = None,
        deferrable: Optional[bool] = None,
        initially_deferred: Optional[bool] = None,
        validation: Optional[ConstraintValidation] = None,
        enforced: Optional[bool] = None,
    ):
        super().__init__(
            dialect,
            TableConstraintType.FOREIGN_KEY,
            name=name,
            columns=columns,
            foreign_key_table=foreign_key_table,
            foreign_key_columns=foreign_key_columns,
            deferrable=deferrable,
            initially_deferred=initially_deferred,
            validation=validation,
            enforced=enforced,
        )
        self.on_delete = on_delete
        self.on_update = on_update
        self.match_type = match_type


class IndexDefinition(BaseExpression):
    """Represents an index definition clause for CREATE TABLE / ADD INDEX.

    ``columns`` accepts plain column names or :class:`BaseExpression`
    instances (functional/expression index columns, e.g. ``LOWER(name)``).

    Statement-level options (§5.16, plan 方案 A) are carried per index so the
    standalone ``CREATE INDEX`` / ``DROP INDEX`` statements can differ one by
    one. ``None`` means "not explicitly declared" — an explicit declaration
    wins over entry-level parameters. They are ignored by the inline path
    (an index riding inside CREATE TABLE cannot carry statement options; the
    deriver raises on the inline path instead).
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_index_definition"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        columns: List[Union[str, "BaseExpression"]],
        unique: bool = False,
        type: Optional[str] = None,
        partial_condition: Optional["SQLPredicate"] = None,
        include_columns: Optional[List[str]] = None,
        if_not_exists: Optional[bool] = None,
        tablespace: Optional[str] = None,
        if_exists: Optional[bool] = None,
        concurrent: Optional[bool] = None,
    ):
        super().__init__(dialect)
        self.name = name
        self.columns = list(columns)
        self.unique = unique
        self.type = type
        self.partial_condition = partial_condition
        self.include_columns = include_columns
        # Statement-level options (§5.16): ``if_not_exists`` (create path),
        # ``tablespace`` (create path), ``if_exists`` (drop path) and
        # ``concurrent`` (create/drop shared).
        self.if_not_exists = if_not_exists
        self.tablespace = tablespace
        self.if_exists = if_exists
        self.concurrent = concurrent


class CreateTableOptions(BaseExpression):
    """Generic creation modifiers for ``CREATE TABLE``.

    Holds only the **generic** (SQL-standard or broadly shared) options:

    **Header modifier** (between ``CREATE`` and ``TABLE``):

    * ``or_replace`` -- ``CREATE OR REPLACE TABLE`` (standard; widely supported)

    **Table-level option** (after the column list):

    * ``comment`` -- inline table-comment clause, carried as a
      :class:`TableCommentClause`. There is **no** SQL-standard table comment
      mechanism: the bare ``COMMENT '<text>'`` table option is a
      MySQL/MariaDB/ClickHouse-family dialect convenience (Snowflake renders
      ``COMMENT = '<text>'``, BigQuery ``OPTIONS(description='<text>')``), and
      the standalone ``COMMENT ON`` statement is a separate de-facto vendor
      mechanism (:class:`CommentOnExpression`), not this clause. Bare comment
      text is **not** accepted — build the clause node explicitly; rendering
      is capability-gated by the statement renderer through
      :meth:`supports_table_comment`, which raises ``UnsupportedFeatureError``
      on dialects without the grammar instead of silently dropping a declared
      comment.

    Backend-specific creation options (``UNLOGGED`` / ``TRANSIENT`` /
    ``ENGINE`` / ``CHARSET`` / table ``COLLATE`` / ``MEMORY_OPTIMIZED`` /
    ``DURABILITY`` / …) live on a backend's own ``XxxCreateTableOptions``
    subclass — they are **not** generic and there is no ``dialect_options``
    bag.

    ``or_replace`` is rendered by ``format_create_table_options``; the
    statement renderer composes the returned qualifier right after ``CREATE``.
    ``comment`` is a clause node rendered by the statement renderer after the
    column list.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_table_options"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        or_replace: bool = False,
        comment: Optional["TableCommentClause"] = None,
    ):
        super().__init__(dialect)
        if comment is not None and not isinstance(comment, TableCommentClause):
            raise TypeError(
                f"comment must be a TableCommentClause, got {type(comment).__name__}"
            )
        self.or_replace = or_replace
        self.comment = comment


class CreateTableExpression(BaseExpression):
    """Represents a comprehensive CREATE TABLE statement supporting full SQL standard features."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: Union[str, "TableExpression"],
        columns: List[ColumnDefinition],  # List of column definitions with constraints
        indexes: Optional[List[IndexDefinition]] = None,  # Table indexes
        table_constraints: Optional[List[TableConstraint]] = None,  # Table-level constraints
        temporary: bool = False,  # TEMPORARY table flag
        if_not_exists: bool = False,  # IF NOT EXISTS flag
        inherits: Optional[List[str]] = None,  # PostgreSQL INHERITS clause
        tablespace: Optional[str] = None,  # Table tablespace (PostgreSQL/Oracle)
        storage_options: Optional["StorageOptionsExpression"] = None,  # Storage options clause
        *,  # Force keyword arguments
        partition: Optional["PartitionClause"] = None,  # Table partitioning specification
        table_options: Optional["CreateTableOptions"] = None,  # CREATE header modifiers
    ):
        super().__init__(dialect)
        if isinstance(table, str):
            self.table = TableExpression(dialect, table)
        elif isinstance(table, TableExpression):
            self.table = table
        else:
            raise TypeError(f"table must be str or TableExpression, got {type(table).__name__}")
        self.columns = columns  # List of column definitions with embedded constraints
        self.indexes = indexes or []  # List of indexes to create
        self.table_constraints = table_constraints or []  # List of table-level constraints
        self.temporary = temporary  # Temporary table flag
        self.if_not_exists = if_not_exists  # IF NOT EXISTS flag
        self.inherits = inherits or []  # Tables to inherit from (PostgreSQL-specific)
        self.tablespace = tablespace  # Tablespace specification
        self.storage_options = storage_options  # Storage options clause (StorageOptionsExpression)
        # Validate partition parameter type
        if partition is not None and not isinstance(partition, PartitionClause):
            raise TypeError(f"partition must be a PartitionClause instance, got {type(partition).__name__}")
        self.partition = partition
        self.table_options = table_options  # CreateTableOptions (header modifiers)

    @property
    def table_name(self) -> str:
        """Get the table name (for backward compatibility)."""
        return self.table.name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_table_statement"


def _normalize_table_reference(
    dialect: "SQLDialectBase",
    ref: Union[str, "TableExpression", Tuple[str, str]],
) -> "TableExpression":
    """Normalize a table reference into a :class:`TableExpression`.

    Accepts the three forms used across the CREATE TABLE family:

    * ``str`` -- bare table name (``"users"``);
    * ``TableExpression`` -- already structured (returned unchanged);
    * ``tuple`` -- ``(schema_name, table_name)`` pair.
    """
    if isinstance(ref, TableExpression):
        return ref
    if isinstance(ref, str):
        return TableExpression(dialect, ref)
    if isinstance(ref, tuple) and len(ref) == 2:
        return TableExpression(dialect, ref[1], schema_name=ref[0])
    raise TypeError(
        f"table reference must be str, TableExpression or (schema, table) tuple, "
        f"got {type(ref).__name__}"
    )


class CreateTableAsExpression(BaseExpression):
    """Represents ``CREATE TABLE ... AS <query>`` (CTAS).

    The table's structure is derived from the result of a query.  Unlike the
    explicit-schema form (:class:`CreateTableExpression`), the body is a query,
    not a column list.

    Rendering is delegated to the dialect's ``format_create_table_as_statement``.
    The generic implementation emits ``AS <query>`` **without parentheses**
    (parenthesising the query is rejected by SQLite and several other engines).
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_table_as_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: Union[str, "TableExpression"],
        as_query: "QueryExpression",
        *,
        columns: Optional[List[ColumnDefinition]] = None,
        temporary: bool = False,
        if_not_exists: bool = False,
        storage_options: Optional["StorageOptionsExpression"] = None,
        with_data: Optional[bool] = None,
    ):
        super().__init__(dialect)
        self.table = _normalize_table_reference(dialect, table)
        if as_query is None:
            raise ValueError("as_query is required for CreateTableAsExpression")
        self.as_query = as_query
        self.columns = list(columns or [])
        self.temporary = temporary
        self.if_not_exists = if_not_exists
        self.storage_options = storage_options
        self.with_data = with_data

    @property
    def table_name(self) -> str:
        """Get the target table name."""
        return self.table.name


class CreateTableLikeExpression(BaseExpression):
    """Represents ``CREATE TABLE ... LIKE <source_table>``.

    Creates a new empty table copying the *definition* (column attributes,
    indexes) of an existing table, without copying data.  This is a vendor
    extension with no SQL-standard syntax:

    * MySQL / MariaDB: ``CREATE TABLE t LIKE src``
    * Snowflake:       ``CREATE TABLE t LIKE src [COPY GRANTS]``
    * BigQuery:        ``CREATE TABLE t LIKE src [OPTIONS (...)]``
    * PostgreSQL:      clause form ``CREATE TABLE t (LIKE src [INCLUDING ...])``
    * ClickHouse:      uses ``AS src`` / ``CLONE AS src`` -- model through
      :class:`CreateTableAsExpression` / :class:`CreateTableCloneExpression`,
      not this class.

    The generic ``format_create_table_like_statement`` raises
    :class:`UnsupportedFeatureError`; dialects that support the form override it.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_table_like_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: Union[str, "TableExpression"],
        like_table: Union[str, "TableExpression", Tuple[str, str]],
        *,
        temporary: bool = False,
        if_not_exists: bool = False,
        like_options: Optional[Any] = None,
    ):
        super().__init__(dialect)
        self.table = _normalize_table_reference(dialect, table)
        self.like_table = _normalize_table_reference(dialect, like_table)
        self.temporary = temporary
        self.if_not_exists = if_not_exists
        # PostgreSQL-specific INCLUDING/EXCLUDING options (dict or list).
        self.like_options = like_options

    @property
    def table_name(self) -> str:
        """Get the target table name."""
        return self.table.name


class CreateTableCloneMode(Enum):
    """Mode of a definition/data copy operation."""

    CLONE = "CLONE"
    COPY = "COPY"


class CreateTableCloneExpression(BaseExpression):
    """Represents ``CREATE TABLE ... CLONE/COPY <source_table>``.

    Zero-copy (or metadata/data copy) creation from an existing table:

    * Snowflake: ``CREATE TABLE t CLONE src [AT|BEFORE (...)] [COPY GRANTS]``
    * BigQuery:  ``CREATE TABLE t CLONE src`` / ``CREATE TABLE t COPY src``
    * ClickHouse: ``CREATE TABLE t CLONE AS src``

    ``mode`` selects CLONE vs COPY where a dialect distinguishes them.
    ``at`` / ``before`` carry time-travel specifications (Snowflake/BigQuery).
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_table_clone_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: Union[str, "TableExpression"],
        source_table: Union[str, "TableExpression", Tuple[str, str]],
        *,
        mode: CreateTableCloneMode = CreateTableCloneMode.CLONE,
        temporary: bool = False,
        if_not_exists: bool = False,
        at: Optional[Any] = None,
        before: Optional[Any] = None,
        copy_grants: bool = False,
    ):
        super().__init__(dialect)
        if not isinstance(mode, CreateTableCloneMode):
            raise TypeError(f"mode must be a CreateTableCloneMode, got {type(mode).__name__}")
        self.table = _normalize_table_reference(dialect, table)
        self.source_table = _normalize_table_reference(dialect, source_table)
        self.mode = mode
        self.temporary = temporary
        self.if_not_exists = if_not_exists
        self.at = at
        self.before = before
        self.copy_grants = copy_grants

    @property
    def table_name(self) -> str:
        """Get the target table name."""
        return self.table.name


class CreateTableFromTemplateExpression(BaseExpression):
    """Represents Snowflake ``CREATE TABLE ... USING TEMPLATE <query>``.

    Derives the table's column definitions from staged files described by a
    query (typically ``INFER_SCHEMA``).  Dialects that do not support this form
    raise :class:`UnsupportedFeatureError` from
    ``format_create_table_using_template``.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_table_using_template"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: Union[str, "TableExpression"],
        template: "QueryExpression",
        *,
        temporary: bool = False,
        if_not_exists: bool = False,
    ):
        super().__init__(dialect)
        self.table = _normalize_table_reference(dialect, table)
        if template is None:
            raise ValueError("template is required for CreateTableFromTemplateExpression")
        self.template = template
        self.temporary = temporary
        self.if_not_exists = if_not_exists

    @property
    def table_name(self) -> str:
        """Get the target table name."""
        return self.table.name


class DropTableExpression(BaseExpression):
    """Represents a DROP TABLE statement conforming to SQL standard.

    SQL Standard Syntax:
        DROP TABLE [IF EXISTS] <table_name> [CASCADE | RESTRICT]

    The CASCADE/RESTRICT options control dependent object handling:
    - CASCADE: Automatically drops dependent objects (views, foreign keys)
    - RESTRICT: Refuses to drop if dependencies exist (default in SQL standard)

    Capability gating is enforced by the dialect's ``format_drop_table_statement``
    helper via the protocol switches ``supports_drop_table_cascade()`` and
    ``supports_drop_table_restrict()``: asking for a behavior the dialect does
    not support raises ``UnsupportedFeatureError`` rather than emitting a token
    the database would reject (or silently drop).

    Database-specific behavior:
    - PostgreSQL: Full CASCADE/RESTRICT support (both switches True)
    - MySQL/MariaDB: CASCADE keyword is parsed but ignored (no functional
      effect); the switches are True to reflect valid syntax, NOT valid
      semantics. Refer to the dialect docstring for the no-op caveat.
    - Oracle: Uses the backend-specific ``CASCADE CONSTRAINTS [PURGE]`` form
      (narrower than SQL-standard CASCADE: only drops referencing constraints,
      not views/triggers). Declared via Oracle's backend protocol and rendered
      by an Oracle-specific override of ``format_drop_table_statement``.
    - SQLite: CASCADE/RESTRICT not recognized; both switches False -> raising.
    - SQL Server: No CASCADE/RESTRICT support; both switches False -> raising.
    - Firebird: No CASCADE/RESTRICT support; both switches False -> raising.

    Args:
        dialect: The SQL dialect to use for formatting
        table_name: The table name (string) or TableExpression object
        if_exists: Add IF EXISTS clause to avoid error if table doesn't exist
        cascade: Optional cascade behavior:
            - None: Omit from SQL (use database default)
            - True: Generate CASCADE (or dialect-specific equivalent form)
            - False: Generate RESTRICT (or raise if unsupported)
        purge: Oracle PURGE via a typed flag which, combined with cascade=True,
            appends PURGE after the dialect-specific cascade form.

    Examples:
        # Simple drop
        DropTableExpression(dialect, "users")
        # -> DROP TABLE users

        # With IF EXISTS
        DropTableExpression(dialect, "users", if_exists=True)
        # -> DROP TABLE IF EXISTS users  (on dialects supporting IF EXISTS)

        # With CASCADE (PostgreSQL / MySQL / MariaDB)
        DropTableExpression(dialect, "users", cascade=True)
        # -> DROP TABLE users CASCADE

        # With CASCADE on Oracle (dialect renders its own form)
        DropTableExpression(oracle_dialect, "users", cascade=True, purge=True)
        # -> DROP TABLE users CASCADE CONSTRAINTS PURGE

        # With schema-qualified table
        DropTableExpression(dialect, TableExpression(dialect, "users", schema_name="public"))
        # -> DROP TABLE public.users
    """
    
    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_table_statement"
    
    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: Union[str, "TableExpression"],
        if_exists: bool = False,
        cascade: Optional[bool] = None,
        purge: bool = False,
    ):
        super().__init__(dialect)
        if isinstance(table, str):
            self.table = TableExpression(dialect, table)
        elif isinstance(table, TableExpression):
            self.table = table
        else:
            raise TypeError(f"table must be str or TableExpression, got {type(table).__name__}")
        self.if_exists = if_exists
        self.cascade = cascade
        self.purge = purge


class StorageOptionsExpression(BaseExpression):
    """Represents a ``WITH (...)`` or storage-options clause.

    Holds a mapping of option names to values.  The dialect formatter renders
    each pair as ``key = <value>`` where the value is inlined via
    ``inline_sql_literal``.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        options: Dict[str, Any],
    ):
        super().__init__(dialect)
        self.options = options

    def to_sql(self) -> SQLQueryAndParams:
        """Delegate to the dialect's ``format_storage_options``."""
        return self.dialect.format_storage_options(self)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_storage_options"
