# src/rhosocial/activerecord/backend/expression/statements.py
"""
SQL DML (Data Manipulation Language), DQL (Data Query Language),
and DDL (Data Definition Language) statements.

These expression classes are responsible for collecting the parameters and structure
for a given SQL statement and delegating the actual SQL string generation
to a backend-specific dialect.
"""
import abc
from typing import Tuple, Any, List, Optional, Dict, Union, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass, field

from . import bases
from . import core
from . import mixins

if TYPE_CHECKING:
    from ..dialect import SQLDialectBase, ExplainOptions
    from .query_clauses import SetOperationExpression, JoinExpression, ValuesExpression, TableFunctionExpression, LateralExpression


# region DML and DQL Statements

# region Merge Statement
class MergeActionType(Enum):
    """Represents the type of action to perform in a MERGE statement."""
    UPDATE = "UPDATE"
    INSERT = "INSERT"
    DELETE = "DELETE"


@dataclass
class MergeAction:
    """
    Represents an action (UPDATE, INSERT, or DELETE) to be performed
    within a MERGE statement's WHEN clause.
    """
    action_type: MergeActionType
    assignments: Optional[Dict[str, "bases.BaseExpression"]] = field(default_factory=dict)
    values: Optional[List["bases.BaseExpression"]] = field(default_factory=list)
    condition: Optional["bases.SQLPredicate"] = None


class MergeExpression(bases.BaseExpression):
    """Represents a MERGE statement."""
    def __init__(self, dialect: "SQLDialectBase",
                 target_table: Union[str, "core.TableExpression"],
                 source: Union["core.Subquery", "core.TableExpression", "ValuesExpression"],
                 on_condition: "bases.SQLPredicate",
                 when_matched: Optional[List[MergeAction]] = None,
                 when_not_matched: Optional[List[MergeAction]] = None):
        super().__init__(dialect)
        self.target_table = target_table if isinstance(target_table, core.TableExpression) else core.TableExpression(dialect, target_table)
        self.source = source
        self.on_condition = on_condition
        self.when_matched = when_matched or []
        self.when_not_matched = when_not_matched or []

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the MERGE statement to the configured dialect."""
        return self.dialect.format_merge_statement(self)
# endregion Merge Statement


# region Query Statement
class QueryExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """Represents a complete SELECT query expression with all clauses."""
    def __init__(self, dialect: "SQLDialectBase",
                 select: List["bases.BaseExpression"],
                 from_: Optional[Union["core.TableExpression", "core.Subquery", "SetOperationExpression", "JoinExpression", "ValuesExpression", "TableFunctionExpression", "LateralExpression", "bases.BaseExpression"]] = None,
                 where: Optional["bases.SQLPredicate"] = None,
                 group_by: Optional[List["bases.BaseExpression"]] = None,
                 having: Optional["bases.SQLPredicate"] = None,
                 order_by: Optional[List["bases.BaseExpression"]] = None,
                 qualify: Optional["bases.SQLPredicate"] = None,
                 limit: Optional[int] = None,
                 offset: Optional[int] = None,
                 for_update_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.select, self.from_, self.where, self.group_by, self.having = select or [], from_, where, group_by or [], having
        self.order_by, self.qualify, self.limit, self.offset, self.for_update_options = order_by or [], qualify, limit, offset, for_update_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the entire SELECT statement to the configured dialect."""
        return self.dialect.format_query_statement(self)
# endregion Query Statement


# region Delete Statement
class DeleteExpression(bases.BaseExpression):
    """
    Represents an SQL DELETE statement, allowing removal of rows from a table.
    It supports specifying a target table, an optional FROM clause for joining
    with other tables or subqueries (behavior and supported sources may vary
    significantly across SQL dialects), a WHERE clause for filtering rows,
    a RETURNING clause, and backend-specific options.
    """
    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: Union[str, "core.TableExpression"],
        *, # Enforce keyword-only arguments for optional parameters
        from_: Optional[Union[
            "core.TableExpression",
            "core.Subquery",
            "SetOperationExpression",
            "JoinExpression",
            List[Union["core.TableExpression", "core.Subquery", "SetOperationExpression", "JoinExpression", "ValuesExpression", "TableFunctionExpression", "LateralExpression"]]
        ]] = None,
        where: Optional["bases.SQLPredicate"] = None,
        returning: Optional[List["bases.BaseExpression"]] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)

        # Normalize the target table to a TableExpression
        self.table = table if isinstance(table, core.TableExpression) else core.TableExpression(dialect, str(table))
        self.from_ = from_
        self.where = where
        self.returning = returning
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the DELETE statement to the configured dialect."""
        return self.dialect.format_delete_statement(self)
# endregion Delete Statement


# region Update Statement
class UpdateExpression(bases.BaseExpression):
    """
    Represents an SQL UPDATE statement, allowing modification of existing rows
    in a table. It supports a target table, assignment of new values to columns,
    an optional FROM clause for joining with other tables or subqueries (behavior
    and supported sources may vary significantly across SQL dialects, e.g.,
    PostgreSQL offers a more flexible FROM than SQLite's more restrictive syntax),
    a WHERE clause for filtering rows, a RETURNING clause, and backend-specific options.
    """
    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: Union[str, "core.TableExpression"],
        assignments: Dict[str, "bases.BaseExpression"],
        *, # Enforce keyword-only arguments for optional parameters
        from_: Optional[Union[ # Optional FROM clause, compatible with various SQL dialects.
                               # SQLite's UPDATE FROM is more restrictive, typically allowing only
                               # a comma-separated list of table-or-subquery or a single JOIN clause.
                               # More advanced SQL dialects (e.g., PostgreSQL) allow richer FROM sources.
            "core.TableExpression",
            "core.Subquery",
            "SetOperationExpression",
            "JoinExpression",
            List[Union["core.TableExpression", "core.Subquery", "SetOperationExpression", "JoinExpression", "ValuesExpression", "TableFunctionExpression", "LateralExpression"]]
        ]] = None,
        where: Optional["bases.SQLPredicate"] = None,
        returning: Optional[List["bases.BaseExpression"]] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)

        # Normalize the target table to a TableExpression
        self.table = table if isinstance(table, core.TableExpression) else core.TableExpression(dialect, str(table))
        self.assignments = assignments
        self.from_ = from_
        self.where = where
        self.returning = returning
        self.dialect_options = dialect_options or {}

        # Basic validation for assignments
        if not self.assignments:
            raise ValueError("Assignments cannot be empty for an UPDATE statement.")

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the UPDATE statement to the configured dialect."""
        return self.dialect.format_update_statement(self)
# endregion Update Statement


# region Insert Statement
class InsertDataSource(abc.ABC):
    """
    Abstract base class for an INSERT statement's data source.
    Implementations represent the source of data, such as a VALUES clause,
    a SELECT query, or the DEFAULT VALUES keyword.
    """
    def __init__(self, dialect: "SQLDialectBase"):
        self._dialect = dialect

    @property
    def dialect(self) -> "SQLDialectBase":
        return self._dialect


class ValuesSource(InsertDataSource):
    """
    Represents a data source from a VALUES clause, where values are provided
    as explicit expressions for insertion into a table.

    The `values_list` parameter defines the rows of data to be inserted.
    Each element in `values_list` is itself a list, representing a single row,
    and each element within a row list must be an expression.

    Currently, the type hint for these expressions is `bases.BaseExpression`.
    This generic type allows for various expression types (e.g., `Literal`, `Column`,
    `RawSQLExpression`, scalar `QueryExpression` as subqueries) to be used as values.
    It is a pragmatic choice given the current stage of framework development.

    However, it's important to note that statement-level expressions (such as
    `InsertExpression`, `UpdateExpression`, `DeleteExpression`, or non-scalar `QueryExpression`)
    are *not* valid elements within `values_list`. These are complete SQL statements
    and do not represent a single value or expression suitable for a `VALUES` clause.

    In future iterations, as the framework matures, the type hint may be refined
    to a more specific `Union` of supported `bases.BaseExpression` derived classes
    (e.g., `Union[Literal, Column, ScalarSubquery]`) to provide stricter type checking
    and clearer developer guidance on what constitutes a valid value expression.
    """
    def __init__(self, dialect: "SQLDialectBase", values_list: List[List["bases.BaseExpression"]]):
        super().__init__(dialect)
        if not values_list or not all(isinstance(row, list) for row in values_list):
            raise ValueError("'values_list' must be a non-empty list of lists.")
        if len(set(len(row) for row in values_list)) > 1:
            raise ValueError("All rows in 'values_list' must have the same number of columns.")
        self.values_list = values_list


class SelectSource(InsertDataSource):
    """Represents a data source from a SELECT subquery."""
    def __init__(self, dialect: "SQLDialectBase", select_query: "QueryExpression"):
        super().__init__(dialect)
        self.select_query = select_query


class DefaultValuesSource(InsertDataSource):
    """Represents the DEFAULT VALUES data source."""
    pass


class OnConflictClause(bases.BaseExpression):
    """
    Represents an ON CONFLICT clause for "upsert" operations, supporting
    both DO NOTHING and DO UPDATE actions.
    """
    def __init__(
        self,
        dialect: "SQLDialectBase",
        conflict_target: Optional[List[Union[str, "bases.BaseExpression"]]],
        *,
        do_nothing: bool = False,
        update_assignments: Optional[Dict[str, "bases.BaseExpression"]] = None,
        update_where: Optional["bases.SQLPredicate"] = None
    ):
        super().__init__(dialect)
        if do_nothing and (update_assignments is not None):
            raise ValueError("Cannot specify both 'do_nothing=True' and 'update_assignments' for ON CONFLICT.")
        if not do_nothing and update_assignments is None:
            raise ValueError("Must specify either 'do_nothing=True' or 'update_assignments' for ON CONFLICT.")

        self.conflict_target = conflict_target
        self.do_nothing = do_nothing
        self.update_assignments = update_assignments
        self.update_where = update_where

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates formatting of the ON CONFLICT clause to the configured dialect."""
        return self.dialect.format_on_conflict_clause(self)


class InsertExpression(bases.BaseExpression):
    """
    Represents a structured INSERT statement, supporting various data sources,
    upsert logic (ON CONFLICT), and RETURNING clauses.
    """
    def __init__(
        self,
        dialect: "SQLDialectBase",
        into: Union[str, "core.TableExpression"],
        source: InsertDataSource,
        columns: Optional[List[str]] = None,
        *,
        on_conflict: Optional[OnConflictClause] = None,
        returning: Optional[List["bases.BaseExpression"]] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)

        self.into = into if isinstance(into, core.TableExpression) else core.TableExpression(dialect, str(into))
        self.source = source
        self.columns = columns
        self.on_conflict = on_conflict
        self.returning = returning
        self.dialect_options = dialect_options or {}

        # Perform validation
        # 1. First, check if on_conflict is used with a valid source
        if on_conflict and not isinstance(source, (ValuesSource, SelectSource)):
            raise ValueError("'on_conflict' is only supported for 'VALUES' or 'SELECT' sources.")

        # 2. Then, check for other misuses of DefaultValuesSource
        if isinstance(source, DefaultValuesSource) and columns:
            raise ValueError("'DEFAULT VALUES' source cannot be used with 'columns'.")

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the INSERT statement to the configured dialect."""
        return self.dialect.format_insert_statement(self)
# endregion Insert Statement


# region Explain Statement
class ExplainExpression(bases.BaseExpression):
    """Represents an EXPLAIN statement."""
    def __init__(self, dialect: "SQLDialectBase",
                 statement: Union[QueryExpression, InsertExpression, UpdateExpression, DeleteExpression],
                 options: Optional["ExplainOptions"] = None):
        super().__init__(dialect)
        self.statement, self.options = statement, options

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the EXPLAIN statement to the configured dialect."""
        return self.dialect.format_explain_statement(self)
# endregion Explain Statement

# endregion DML and DQL Statements


# region DDL Expressions

@dataclass
class ColumnDefinition:
    """Represents a column's definition within a CREATE/ALTER TABLE statement."""
    name: str
    data_type: str
    nullable: Optional[bool] = None
    primary_key: bool = False
    default: Any = None
    # Future constraints can be added here, e.g., unique, check.


@dataclass
class IndexDefinition:
    """Represents an index definition for a table."""
    name: str
    columns: List[str]
    unique: bool = False


class CreateTableExpression(bases.BaseExpression):
    """Represents a CREATE TABLE statement."""
    def __init__(self, dialect: "SQLDialectBase", table_name: str,
                 columns: List[ColumnDefinition],
                 indexes: Optional[List[IndexDefinition]] = None,
                 if_not_exists: bool = False):
        super().__init__(dialect)
        self.table_name = table_name
        self.columns = columns
        self.indexes = indexes or []
        self.if_not_exists = if_not_exists

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the CREATE TABLE statement to the configured dialect."""
        return self.dialect.format_create_table_statement(self)


class DropTableExpression(bases.BaseExpression):
    """Represents a DROP TABLE statement."""
    def __init__(self, dialect: "SQLDialectBase", table_name: str, if_exists: bool = False):
        super().__init__(dialect)
        self.table_name = table_name
        self.if_exists = if_exists

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the DROP TABLE statement to the configured dialect."""
        return self.dialect.format_drop_table_statement(self)


class AlterTableAction(abc.ABC):
    """Abstract base class for a single action within an ALTER TABLE statement."""
    pass


@dataclass
class AddColumn(AlterTableAction):
    """Represents an 'ADD COLUMN' action."""
    column: ColumnDefinition


@dataclass
class DropColumn(AlterTableAction):
    """Represents a 'DROP COLUMN' action."""
    column_name: str


class AlterTableExpression(bases.BaseExpression):
    """Represents an ALTER TABLE statement."""
    def __init__(self, dialect: "SQLDialectBase", table_name: str, actions: List[AlterTableAction]):
        super().__init__(dialect)
        self.table_name = table_name
        self.actions = actions

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the ALTER TABLE statement to the configured dialect."""
        return self.dialect.format_alter_table_statement(self)

# endregion DDL Expressions