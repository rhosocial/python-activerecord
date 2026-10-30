# src/rhosocial/activerecord/backend/impl/sqlite/expression/introspection.py
"""
SQLite-specific introspection expressions.

This module carries the introspection questions SQLite answers in its own
vocabulary:

- ``PRAGMA``: a statement of its own, expressed by no portable grammar node,
  so it has two statement classes and two formatters on the SQLite dialect.
- column information with hidden columns, which PRAGMA ``table_xinfo`` reports
  and PRAGMA ``table_info`` does not.
- the table count and the stored DDL of a table or index, which live in
  ``sqlite_master``: SQLite keeps the statement text that created each object,
  and no portable catalogue holds it.

They live here rather than in core: core carries the families every engine
shares, and these are not among them.
"""

from typing import Any, Optional, TYPE_CHECKING

from ....expression.introspection import ColumnInfoQueryStatement, IntrospectionExpression

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase


class SQLiteColumnInfoExpression(ColumnInfoQueryStatement):
    """SQLite column information expression.

    Extends ColumnInfoQueryStatement with SQLite-specific parameters.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        table_name: The name of the table to query columns for.
        schema: Optional schema name. Defaults to None.
        include_hidden: Whether to include hidden columns. Defaults to False.
        use_xinfo_pragma: Whether to use PRAGMA table_xinfo instead of table_info.
            PRAGMA table_xinfo includes hidden columns and is available in SQLite 3.26.0+.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        schema: Optional[str] = None,
        include_hidden: bool = False,
        use_xinfo_pragma: bool = False,
    ):
        super().__init__(dialect, table_name, schema, include_hidden)
        self.use_xinfo_pragma = use_xinfo_pragma


class SQLitePragmaQueryStatement(IntrospectionExpression):
    """A ``PRAGMA`` question: what does this pragma currently answer?

    PRAGMA accepts no bind parameters, so everything the engine needs is in the
    statement text. The ``argument`` is therefore carried in the spelling the
    engine expects (a bare name, a quoted identifier) and placed verbatim by
    the formatter; it is never re-quoted here.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        name: PRAGMA name, such as ``"journal_mode"``.
        argument: Optional argument the pragma takes, already spelled for the
            engine (for example ``"'users'"`` for ``table_info``).
        schema: Optional attached-database name, such as ``"temp"``.

    Example:
        >>> expr = SQLitePragmaQueryStatement(dialect, "table_info", "'users'")
        >>> sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        argument: Optional[Any] = None,
        schema: Optional[str] = None,
    ):
        super().__init__(dialect, schema)
        self.name: str = name
        self.argument: Optional[Any] = argument

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_pragma_query_statement"


class SQLitePragmaSetStatement(IntrospectionExpression):
    """A ``PRAGMA`` assignment: give this pragma a value.

    Like :class:`SQLitePragmaQueryStatement`, this carries no bind parameters:
    the formatter decides how the value is written, because PRAGMA takes its
    value as statement text.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        name: PRAGMA name, such as ``"journal_mode"``.
        value: The value to assign.
        argument: Optional argument the pragma takes, already spelled for the
            engine.
        schema: Optional attached-database name, such as ``"main"``.

    Example:
        >>> expr = SQLitePragmaSetStatement(dialect, "journal_mode", "WAL")
        >>> sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        value: Any,
        argument: Optional[Any] = None,
        schema: Optional[str] = None,
    ):
        super().__init__(dialect, schema)
        self.name: str = name
        self.value: Any = value
        self.argument: Optional[Any] = argument

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_pragma_set_statement"


class SQLiteTableCountStatement(IntrospectionExpression):
    """How many tables one database declares, system tables excluded.

    The count is a question about ``sqlite_master``, whose name is this
    backend's own vocabulary; the dialect formats it as a ``SELECT COUNT(*)``
    over that relation rather than as a PRAGMA, because SQLite offers no
    PRAGMA that counts tables without listing them first.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        schema: The database to count, such as ``"main"`` or ``"temp"``.
            Defaults to the primary database.

    Example:
        >>> expr = SQLiteTableCountStatement(dialect, "main")
        >>> sql, params = expr.to_sql()
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_count_statement"


class SQLiteTableDdlStatement(IntrospectionExpression):
    """The DDL a table was declared with, as ``sqlite_master`` stores it.

    SQLite keeps the statement text that created each object, so the DDL is
    read back rather than reassembled from column and constraint facts. The
    table is matched by both ``name`` and ``tbl_name``: an index row carries
    the indexed table in ``tbl_name``, and a table row carries its own name in
    both, so requiring both selects the table row alone.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        table_name: The table whose DDL is read.
        schema: The database holding the table, such as ``"main"``.
            Defaults to the primary database.

    Example:
        >>> expr = SQLiteTableDdlStatement(dialect, "users")
        >>> sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        schema: Optional[str] = None,
    ):
        super().__init__(dialect, schema)
        self.table_name: str = table_name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_ddl_statement"


class SQLiteIndexDdlStatement(IntrospectionExpression):
    """The DDL an index was declared with, as ``sqlite_master`` stores it.

    A partial index's filter condition exists nowhere else: PRAGMA
    ``index_list`` reports only that the index is partial, and ``index_xinfo``
    reports its columns, so the ``WHERE`` clause has to be read back from the
    statement text.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        index_name: The index whose DDL is read.
        schema: The database holding the index, such as ``"main"``.
            Defaults to the primary database.

    Example:
        >>> expr = SQLiteIndexDdlStatement(dialect, "idx_users_email")
        >>> sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index_name: str,
        schema: Optional[str] = None,
    ):
        super().__init__(dialect, schema)
        self.index_name: str = index_name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_index_ddl_statement"
