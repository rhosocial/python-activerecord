# src/rhosocial/activerecord/backend/expression/statements/dml.py
"""DML (Data Manipulation Language) statement expressions."""

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

from ..bases import BaseExpression, SQLPredicate, SQLQueryAndParams
from ..core import TableExpression, Subquery
from ..query_parts import WhereClause

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from ..query_sources import ValuesExpression, TableFunctionExpression, LateralExpression, SetOperationExpression
    from ..query_parts import JoinExpression


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
    assignments: Optional[Dict[str, "BaseExpression"]] = field(default_factory=dict)  # For UPDATE SET clause
    values: Optional[List["BaseExpression"]] = field(default_factory=list)  # For INSERT VALUES clause
    condition: Optional["SQLPredicate"] = None  # Optional additional condition for the WHEN clause


class MergeExpression(BaseExpression):
    """
    Represents a SQL MERGE statement conforming to SQL standard syntax.

    The MERGE statement performs conditional processing based on whether a row
    exists in the target table that matches the source row according to the ON condition.

    Basic syntax:
        MERGE INTO target_table
        USING source
        ON condition
        WHEN MATCHED THEN action
        WHEN NOT MATCHED THEN action
        [WHEN NOT MATCHED BY SOURCE THEN action];

    Example:
        # Simple merge: update if exists, insert if not
        merge = MergeExpression(
            dialect,
            target_table="products",
            source=ValuesSource(dialect, [[1, "Product A", 19.99]], "new_products", ["id", "name", "price"]),
            on_condition=Column(dialect, "id", "tgt") == Column(dialect, "id", "src"),
            when_matched=[
                MergeAction(
                    action_type=MergeActionType.UPDATE,
                    assignments={
                        "name": Column(dialect, "name", "src"),
                        "price": Column(dialect, "price", "src")
                    }
                )
            ],
            when_not_matched=[
                MergeAction(
                    action_type=MergeActionType.INSERT,
                    assignments={
                        "id": Column(dialect, "id", "src"),
                        "name": Column(dialect, "name", "src"),
                        "price": Column(dialect, "price", "src")
                    }
                )
            ]
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        target_table: Union[str, "TableExpression"],
        source: Union[
            "Subquery", "TableExpression", "ValuesExpression", "TableFunctionExpression", "LateralExpression"
        ],
        on_condition: "SQLPredicate",  # The main matching condition
        when_matched: Optional[List[MergeAction]] = None,  # WHEN MATCHED THEN ...
        when_not_matched: Optional[List[MergeAction]] = None,  # WHEN NOT MATCHED THEN ...
        when_not_matched_by_source: Optional[List[MergeAction]] = None,
    ):  # WHEN NOT MATCHED BY SOURCE THEN ... (not supported by all DBs)
        super().__init__(dialect)
        self.target_table = (
            target_table
            if isinstance(target_table, TableExpression)
            else TableExpression(dialect, str(target_table))
        )
        self.source = source
        self.on_condition = on_condition
        self.when_matched = when_matched or []
        self.when_not_matched = when_not_matched or []
        self.when_not_matched_by_source = when_not_matched_by_source or []

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegates SQL generation for the MERGE statement to the configured dialect."""
        return self.dialect.format_merge_statement(self)


# endregion Merge Statement


class ReturningClause(BaseExpression):
    """
    Represents a RETURNING clause used in INSERT, UPDATE, and DELETE statements.

    The RETURNING clause allows retrieval of values from modified rows during
    DML operations, which is useful for obtaining auto-generated values, or
    for audit trails. The specific syntax and supported expressions may vary
    significantly between different SQL databases.

    This class follows the framework pattern of collecting parameters and
    delegating SQL generation to the specific dialect.

    Example Usage:
        # Basic RETURNING clause with columns
        returning_clause = ReturningClause(
            dialect,
            expressions=[Column(dialect, "id"), Column(dialect, "created_at")]
        )

        # RETURNING clause with computed expressions
        returning_clause = ReturningClause(
            dialect,
            expressions=[
                Column(dialect, "id"),
                FunctionCall(dialect, "NOW"),
                Literal(dialect, "updated")  # Constant value
            ],
            alias="modified_rows"
        )

        # RETURNING * to return all columns
        returning_clause = ReturningClause(
            dialect,
            expressions=[RawSQLExpression(dialect, "*")]  # Use RawSQL for asterisk
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expressions: List["BaseExpression"],  # List of expressions to return
        alias: Optional[str] = None,  # Optional alias for the returning result
        dialect_options: Optional[Dict[str, Any]] = None,
    ):  # Dialect-specific options
        super().__init__(dialect)
        self.expressions = expressions or []
        self.alias = alias  # Optional alias for the returning clause
        self.dialect_options = dialect_options or {}  # Dialect-specific options

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates to dialect for RETURNING clause SQL generation."""
        return self.dialect.format_returning_clause(self)


# region Delete Statement
class DeleteExpression(BaseExpression):
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
        table: Union[str, "TableExpression", List[Union[str, "TableExpression"]]],
        *,  # Enforce keyword-only arguments for optional parameters
        using: Optional[
            Union[
                "TableExpression",
                "Subquery",
                "SetOperationExpression",
                "JoinExpression",
                List[
                    Union[
                        "TableExpression",
                        "Subquery",
                        "SetOperationExpression",
                        "JoinExpression",
                        "ValuesExpression",
                        "TableFunctionExpression",
                        "LateralExpression",
                    ]
                ],
            ]
        ] = None,
        where: Optional[Union["SQLPredicate", "WhereClause"]] = None,  # WHERE condition or clause object
        returning: Optional["ReturningClause"] = None,  # RETURNING clause object
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)

        # Normalize the target table(s) to a list of TableExpression objects
        if isinstance(table, list):
            if not table:
                raise ValueError("Table list cannot be empty for a DELETE statement.")
            self.tables = []
            for t in table:
                if isinstance(t, TableExpression):
                    self.tables.append(t)
                else:
                    self.tables.append(TableExpression(dialect, str(t)))
        else:
            # Single table
            single_table = (
                table if isinstance(table, TableExpression) else TableExpression(dialect, str(table))
            )
            self.tables = [single_table]

        self.using = using

        # Handle where parameter: accept either a predicate or a WhereClause object
        if where is not None:
            if isinstance(where, WhereClause):
                self.where = where  # Already a WhereClause object
            else:
                # Wrap a predicate in a WhereClause object
                self.where = WhereClause(dialect, condition=where)
        else:
            self.where = None

        self.returning = returning  # RETURNING clause object
        self.dialect_options = dialect_options or {}

    def validate(self, strict: bool = True) -> None:
        """Validate DeleteExpression parameters according to SQL standard.

        Args:
            strict: If True, perform strict validation that may impact performance.
                   If False, skip validation for performance optimization.

        Raises:
            TypeError: If validation fails with incorrect parameter types
            ValueError: If validation fails with invalid values
        """
        if not strict:
            return

        # Validate tables parameter (already normalized in constructor)
        if not isinstance(self.tables, list):
            raise TypeError(f"tables must be a list of tables, got {type(self.tables)}")
        if not self.tables:
            raise ValueError("Tables cannot be empty for a DELETE statement.")
        for i, table in enumerate(self.tables):
            if not isinstance(table, TableExpression):
                raise TypeError(f"tables[{i}] must be TableExpression, got {type(table)}")

        # Validate using parameter
        if self.using is not None:
            # Check if it's one of the valid types using isinstance with type names
            valid_types = (str, TableExpression, Subquery)
            if not isinstance(self.using, valid_types) and not isinstance(self.using, list):
                # For complex types, check their type names
                using_type_name = type(self.using).__name__
                valid_type_names = [
                    "SetOperationExpression",
                    "JoinExpression",
                    "ValuesExpression",
                    "TableFunctionExpression",
                    "LateralExpression",
                    "QueryExpression",
                ]
                if using_type_name not in valid_type_names:
                    raise TypeError(
                        f"using must be one of: str, TableExpression, Subquery, SetOperationExpression, "
                        f"JoinExpression, list, ValuesExpression, TableFunctionExpression, "
                        f"LateralExpression, QueryExpression, got {type(self.using)}"
                    )

        # Validate where parameter
        if self.where is not None and not isinstance(self.where, (WhereClause, SQLPredicate)):
            raise TypeError(f"where must be WhereClause or SQLPredicate, got {type(self.where)}")

        # Validate returning parameter
        if self.returning is not None and not isinstance(self.returning, ReturningClause):
            raise TypeError(f"returning must be ReturningClause, got {type(self.returning)}")

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegates SQL generation for the DELETE statement to the configured dialect."""
        return self.dialect.format_delete_statement(self)


# endregion Delete Statement


# region Update Statement
class UpdateExpression(BaseExpression):
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
        table: Union[str, "TableExpression"],
        assignments: Dict[str, "BaseExpression"],
        *,  # Enforce keyword-only arguments for optional parameters
        from_: Optional[
            Union[  # Optional FROM clause, compatible with various SQL dialects.
                # SQLite's UPDATE FROM is more restrictive, typically allowing only
                # a comma-separated list of table-or-subquery or a single JOIN clause.
                # More advanced SQL dialects (e.g., PostgreSQL) allow richer FROM sources.
                "TableExpression",
                "Subquery",
                "SetOperationExpression",
                "JoinExpression",
                List[
                    Union[
                        "TableExpression",
                        "Subquery",
                        "SetOperationExpression",
                        "JoinExpression",
                        "ValuesExpression",
                        "TableFunctionExpression",
                        "LateralExpression",
                    ]
                ],
            ]
        ] = None,
        where: Optional[Union["SQLPredicate", "WhereClause"]] = None,  # WHERE condition or clause object
        returning: Optional["ReturningClause"] = None,  # RETURNING clause object
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)

        # Validate assignments
        if not assignments:
            raise ValueError("Assignments cannot be empty for an UPDATE statement.")

        # Normalize the target table to a TableExpression
        self.table = table if isinstance(table, TableExpression) else TableExpression(dialect, str(table))
        self.assignments = assignments
        self.from_ = from_

        # Handle where parameter: accept either a predicate or a WhereClause object
        if where is not None:
            if isinstance(where, WhereClause):
                self.where = where  # Already a WhereClause object
            else:
                # Wrap a predicate in a WhereClause object
                self.where = WhereClause(dialect, condition=where)
        else:
            self.where = None

        self.returning = returning  # RETURNING clause object
        self.dialect_options = dialect_options or {}

    def validate(self, strict: bool = True) -> None:
        """Validate UpdateExpression parameters according to SQL standard.

        Args:
            strict: If True, perform strict validation that may impact performance.
                   If False, skip validation for performance optimization.

        Raises:
            TypeError: If validation fails with incorrect parameter types
        """
        if not strict:
            return

        # Note: The table parameter is normalized in the constructor to always be a TableExpression,
        # so we don't need to validate its type here.

        # Validate assignments parameter
        if not isinstance(self.assignments, dict):
            raise TypeError(f"assignments must be dict, got {type(self.assignments)}")

        # Validate from_ parameter
        if self.from_ is not None:
            # Check if it's one of the valid types using isinstance with type names
            valid_types = (str, TableExpression, Subquery)
            if not isinstance(self.from_, valid_types) and not isinstance(self.from_, list):
                # For complex types, check their type names
                from_type_name = type(self.from_).__name__
                valid_type_names = [
                    "SetOperationExpression",
                    "JoinExpression",
                    "ValuesExpression",
                    "TableFunctionExpression",
                    "LateralExpression",
                ]
                if from_type_name not in valid_type_names:
                    raise TypeError(
                        f"from_ must be one of: str, TableExpression, Subquery, SetOperationExpression, "
                        f"JoinExpression, list, ValuesExpression, TableFunctionExpression, "
                        f"LateralExpression, got {type(self.from_)}"
                    )

        # Validate where parameter
        if self.where is not None and not isinstance(self.where, (WhereClause, SQLPredicate)):
            raise TypeError(f"where must be WhereClause or SQLPredicate, got {type(self.where)}")

        # Validate returning parameter
        if self.returning is not None and not isinstance(self.returning, ReturningClause):
            raise TypeError(f"returning must be ReturningClause, got {type(self.returning)}")

    def to_sql(self) -> "SQLQueryAndParams":
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

    Currently, the type hint for these expressions is `BaseExpression`.
    This generic type allows for various expression types (e.g., `Literal`, `Column`,
    `RawSQLExpression`, scalar `QueryExpression` as subqueries) to be used as values.
    It is a pragmatic choice given the current stage of framework development.

    However, it's important to note that statement-level expressions (such as
    `InsertExpression`, `UpdateExpression`, `DeleteExpression`, or non-scalar `QueryExpression`)
    are *not* valid elements within `values_list`. These are complete SQL statements
    and do not represent a single value or expression suitable for a `VALUES` clause.

    In future iterations, as the framework matures, the type hint may be refined
    to a more specific `Union` of supported `BaseExpression` derived classes
    (e.g., `Union[Literal, Column, ScalarSubquery]`) to provide stricter type checking
    and clearer developer guidance on what constitutes a valid value expression.
    """

    def __init__(self, dialect: "SQLDialectBase", values_list: List[List["BaseExpression"]]):
        super().__init__(dialect)
        if not values_list or not all(isinstance(row, list) for row in values_list):
            raise ValueError("'values_list' must be a non-empty list of lists.")
        if len({len(row) for row in values_list}) > 1:
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


class OnConflictClause(BaseExpression):
    """
    Represents an ON CONFLICT clause for "upsert" operations, supporting
    both DO NOTHING and DO UPDATE actions.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        conflict_target: Optional[List[Union[str, "BaseExpression"]]],
        *,
        do_nothing: bool = False,
        update_assignments: Optional[Dict[str, "BaseExpression"]] = None,
        update_where: Optional["SQLPredicate"] = None,
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

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegates formatting of the ON CONFLICT clause to the configured dialect."""
        return self.dialect.format_on_conflict_clause(self)


class InsertExpression(BaseExpression):
    """
    Represents a structured INSERT statement, supporting various data sources,
    upsert logic (ON CONFLICT), and RETURNING clauses.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        into: Union[str, "TableExpression"],
        source: InsertDataSource,
        columns: Optional[List[str]] = None,
        *,
        on_conflict: Optional[OnConflictClause] = None,
        returning: Optional["ReturningClause"] = None,  # Using ReturningClause instead of list of expressions
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)

        self.into = into if isinstance(into, TableExpression) else TableExpression(dialect, str(into))
        self.source = source
        self.columns = columns
        self.on_conflict = on_conflict
        self.returning = returning  # ReturningClause object or None
        self.dialect_options = dialect_options or {}

        # Perform validation
        # 1. First, check if on_conflict is used with a valid source
        if on_conflict and not isinstance(source, (ValuesSource, SelectSource)):
            raise ValueError("'on_conflict' is only supported for 'VALUES' or 'SELECT' sources.")

        # 2. Then, check for other misuses of DefaultValuesSource
        if isinstance(source, DefaultValuesSource) and columns:
            raise ValueError("'DEFAULT VALUES' source cannot be used with 'columns'.")

    def validate(self, strict: bool = True) -> None:
        """Validate InsertExpression parameters according to SQL standard.

        Args:
            strict: If True, perform strict validation that may impact performance.
                   If False, skip validation for performance optimization.

        Raises:
            TypeError: If validation fails with incorrect parameter types
        """
        if not strict:
            return

        # Validate into parameter
        if not isinstance(self.into, (str, TableExpression)):
            raise TypeError(f"into must be str or TableExpression, got {type(self.into)}")

        # Validate source parameter
        if not isinstance(self.source, InsertDataSource):
            raise TypeError(f"source must be InsertDataSource, got {type(self.source)}")

        # Validate columns parameter
        if self.columns is not None and not isinstance(self.columns, list):
            raise TypeError(f"columns must be list of strings or None, got {type(self.columns)}")

        # Validate on_conflict parameter
        if self.on_conflict is not None and not isinstance(self.on_conflict, OnConflictClause):
            raise TypeError(f"on_conflict must be OnConflictClause, got {type(self.on_conflict)}")

        # Validate returning parameter
        if self.returning is not None and not isinstance(self.returning, ReturningClause):
            raise TypeError(f"returning must be ReturningClause, got {type(self.returning)}")

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegates SQL generation for the INSERT statement to the configured dialect."""
        return self.dialect.format_insert_statement(self)


# endregion Insert Statement
