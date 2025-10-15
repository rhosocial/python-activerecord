# src/rhosocial/activerecord/query/cte.py
"""Common Table Expression (CTE) query mixin implementation."""
import logging
from typing import Dict, List, Optional, Union, Any, Tuple, Type, Set

from .expression import AggregateExpression
from ..backend.errors import CTENotSupportedError
from ..interface import ModelT, IQuery
from .aggregate import AggregateQueryMixin


class CTEQueryMixin(AggregateQueryMixin[ModelT]):
    """Query mixin for Common Table Expressions (CTE) support.

    This mixin provides methods for working with CTEs in SQL queries, allowing
    for more readable and maintainable complex queries, recursive queries,
    and improved query performance through materialization hints.

    CTEs are defined using the WITH clause in SQL and act as temporary named
    result sets that can be referenced multiple times within a query.

    Features:
    - Define CTEs using SQL strings or ActiveQuery instances
    - Support for recursive CTEs
    - Support for materialization hints (when database supports it)
    - Support for multiple CTEs in a single query
    - Chain method calls for building complex queries incrementally
    """

    def __init__(self, model_class: Type[ModelT]):
        """Initialize CTE query mixin.

        Args:
            model_class: Model class this query operates on
        """
        super().__init__(model_class)
        # Dictionary to store CTE definitions
        self._ctes: Dict[str, Dict[str, Any]] = {}
        # Flag to indicate if this query should use CTEs
        self._using_ctes = False
        # Current CTE source when using from_cte()
        self._cte_source = None
        # CTE alias if specified
        self._cte_alias = None

    def supports_cte(self) -> bool:
        """Check if the database supports CTEs.

        Returns:
            bool: True if CTEs are supported by the current database
        """
        dialect = self.model_class.backend().dialect
        return hasattr(dialect, 'cte_handler') and dialect.cte_handler.is_supported

    def supports_recursive_cte(self) -> bool:
        """Check if the database supports recursive CTEs.

        Returns:
            bool: True if recursive CTEs are supported by the current database
        """
        dialect = self.model_class.backend().dialect
        return (hasattr(dialect, 'cte_handler') and
                dialect.cte_handler.is_supported and
                dialect.cte_handler.supports_recursive)

    def supports_materialized_hint(self) -> bool:
        """Check if the database supports materialization hints.

        Returns:
            bool: True if materialization hints are supported by the current database
        """
        dialect = self.model_class.backend().dialect
        return (hasattr(dialect, 'cte_handler') and
                dialect.cte_handler.is_supported and
                dialect.cte_handler.supports_materialized_hint)

    def supports_multiple_ctes(self) -> bool:
        """Check if the database supports multiple CTEs in a single query.

        Returns:
            bool: True if multiple CTEs are supported by the current database
        """
        dialect = self.model_class.backend().dialect
        return (hasattr(dialect, 'cte_handler') and
                dialect.cte_handler.is_supported and
                dialect.cte_handler.supports_multiple_ctes)

    def supports_cte_in_dml(self) -> bool:
        """Check if the database supports CTEs in DML statements.

        Returns:
            bool: True if CTEs in DML statements are supported by the current database
        """
        dialect = self.model_class.backend().dialect
        return (hasattr(dialect, 'cte_handler') and
                dialect.cte_handler.is_supported and
                dialect.cte_handler.supports_cte_in_dml)

    def with_cte(self, name: str, query: Union[str, 'IQuery'],
                 columns: Optional[List[str]] = None,
                 recursive: bool = False,
                 materialized: Optional[bool] = None) -> 'CTEQueryMixin':
        """Define a Common Table Expression (CTE) to use in this query.

        This method adds a named CTE to the query, which can then be referenced
        in the main query or in other CTEs. Multiple CTEs can be added to a
        single query.

        Args:
            name: Name for the CTE (must be a valid SQL identifier)
            query: Either a SQL string or an ActiveQuery instance
            columns: Optional list of column names for the CTE
            recursive: Whether this is a recursive CTE
            materialized: Materialization hint (True=MATERIALIZED,
                         False=NOT MATERIALIZED, None=no hint)

        Returns:
            Query instance for method chaining

        Raises:
            CTENotSupportedError: If CTEs are not supported by the database
            CTENotSupportedError: If recursive CTEs are requested but not supported
            TypeError: If query is not a string or IQuery instance
            Warning: If materialization hints are requested but not supported (logs warning and ignores)

        Warning:
            When using a string for the 'query' parameter, be aware of SQL injection risks.
            Never use string concatenation with untrusted input to build your CTE query.
            Instead, use ActiveQuery instances which properly parameterize values, or
            use placeholders (?) in your string and provide parameters to the query methods
            that use the CTE.

        Examples:
            # Using a SQL string
            User.query().with_cte(
                "active_users",
                "SELECT * FROM users WHERE status = 'active'"
            ).from_cte("active_users").all()

            # Using an ActiveQuery instance (RECOMMENDED for security)
            active_users_query = User.query().where("status = ?", ("active",))
            User.query().with_cte(
                "active_users",
                active_users_query
            ).from_cte("active_users").order_by("name").all()

            # Recursive CTE example (finds all subordinates)
            Employee.query().with_cte(
                "subordinates",
                "SELECT id, name, manager_id FROM employees WHERE id = 1 "
                "UNION ALL "
                "SELECT e.id, e.name, e.manager_id FROM employees e "
                "JOIN subordinates s ON e.manager_id = s.id",
                recursive=True
            ).from_cte("subordinates").all()
        """
        # Check if database supports CTEs
        self._check_cte_support()

        # Check if recursive CTE is supported when requested
        if recursive and not self.supports_recursive_cte():
            dialect = self.model_class.backend().dialect
            raise CTENotSupportedError(
                f"Recursive CTEs are not supported by {dialect.__class__.__name__}"
            )

        # Check if materialization hint is supported when specified
        if materialized is not None and not self.supports_materialized_hint():
            dialect = self.model_class.backend().dialect
            self._log(logging.WARNING,
                      f"Materialization hints are not supported by {dialect.__class__.__name__}. "
                      f"The hint will be ignored.")
            # Setting materialized to None will make it ignored later
            materialized = None

        # Check if multiple CTEs are supported when adding more than one
        if len(self._ctes) > 0 and not self.supports_multiple_ctes():
            dialect = self.model_class.backend().dialect
            raise CTENotSupportedError(
                f"Multiple CTEs are not supported by {dialect.__class__.__name__}"
            )

        # Check if a CTE with this name already exists
        if name in self._ctes:
            self._log(logging.WARNING, f"Overwriting existing CTE: {name}")

        # Process query based on its type
        if isinstance(query, str):
            # It's a SQL string, use as-is
            query_sql = query
            params = ()
        elif isinstance(query, IQuery):
            # It's an ActiveQuery instance, get its SQL and params
            # Explicitly use to_sql method which is now required in IQuery
            query_sql, params = query.to_sql()
        else:
            raise TypeError(f"Expected query to be a string or IQuery instance, got {type(query).__name__}")

        # Store the CTE definition
        self._ctes[name] = {
            'name': name,
            'query': query_sql,
            'params': params,
            'columns': columns,
            'recursive': recursive,
            'materialized': materialized
        }

        # Mark that we're using CTEs
        self._using_ctes = True

        self._log(logging.DEBUG, f"Added CTE: {name}, recursive={recursive}")
        return self

    def from_cte(self, cte_name: str, alias: Optional[str] = None) -> 'CTEQueryMixin':
        """Use a previously defined CTE as the source of this query.

        This method modifies the query to select from the specified CTE
        instead of the model's table. This is particularly useful for
        complex queries where the CTE does significant filtering or joins.

        Args:
            cte_name: Name of a previously defined CTE
            alias: Optional alias for the CTE in the FROM clause

        Returns:
            Query instance for method chaining

        Raises:
            ValueError: If the CTE name is not defined

        Examples:
            User.query()\\
                .with_cte("active_users",
                          "SELECT * FROM users WHERE status = 'active'")\\
                .from_cte("active_users")\\
                .order_by("created_at DESC")\\
                .all()
        """
        # Check if this CTE has been defined
        if cte_name not in self._ctes:
            self._log(logging.ERROR, f"CTE not defined: {cte_name}")
            raise ValueError(f"CTE '{cte_name}' has not been defined. "
                             f"Use with_cte() first to define it.")

        # Store the CTE source for use in building the query
        self._cte_source = cte_name
        self._cte_alias = alias

        # Clear any existing FROM clause to ensure we select from the CTE
        if hasattr(self, '_from_clause'):
            self._from_clause = None

        self._log(logging.DEBUG, f"Using CTE as source: {cte_name}")
        return self

    def with_recursive_cte(self, name: str, query: Union[str, 'IQuery'],
                           columns: Optional[List[str]] = None,
                           materialized: Optional[bool] = None) -> 'CTEQueryMixin':
        """Define a recursive CTE (shorthand for with_cte with recursive=True).

        This is a convenience method that's equivalent to calling with_cte()
        with recursive=True.

        Args:
            name: Name for the CTE (must be a valid SQL identifier)
            query: Either a SQL string or an ActiveQuery instance
            columns: Optional list of column names for the CTE
            materialized: Materialization hint

        Returns:
            Query instance for method chaining

        Examples:
            # Find all subordinates in an organization chart
            Employee.query()\\
                .with_recursive_cte(
                    "subordinates",
                    "SELECT id, name, manager_id FROM employees WHERE id = 1 "
                    "UNION ALL "
                    "SELECT e.id, e.name, e.manager_id FROM employees e "
                    "JOIN subordinates s ON e.manager_id = s.id"
                )\\
                .from_cte("subordinates")\\
                .all()
        """
        return self.with_cte(
            name=name,
            query=query,
            columns=columns,
            recursive=True,
            materialized=materialized
        )

    def _check_cte_support(self) -> None:
        """Check if database dialect supports CTEs.

        Raises:
            CTENotSupportedError: If CTEs are not supported
        """
        if not self.supports_cte():
            dialect = self.model_class.backend().dialect
            raise CTENotSupportedError(
                f"CTEs are not supported by {dialect.__class__.__name__}"
            )

    def _build_cte_clause(self) -> Tuple[Optional[str], List[Any]]:
        """Build the WITH clause for CTEs and collect all parameters.

        This method delegates the actual SQL generation to the database dialect's
        CTE handler, focusing only on collecting CTE definitions and parameters.

        Returns:
            Tuple of (WITH clause SQL, parameters)
        """
        if not self._using_ctes or not self._ctes:
            return None, []

        # Get dialect and CTE handler
        dialect = self.model_class.backend().dialect
        cte_handler = dialect.cte_handler

        # Check recursive support for any recursive CTEs
        for cte in self._ctes.values():
            if cte.get('recursive', False) and not self.supports_recursive_cte():
                raise CTENotSupportedError(
                    f"Recursive CTEs are not supported by {dialect.__class__.__name__}"
                )

        # Pass the raw CTE definitions to the dialect handler
        # Let the handler decide how to format them according to database-specific rules
        ctes_list = list(self._ctes.values())

        # Build WITH clause using dialect handler
        with_clause = cte_handler.format_with_clause(ctes_list)

        # Collect all parameters from CTE definitions
        all_params = []
        for cte in self._ctes.values():
            all_params.extend(cte.get('params', []))

        return with_clause, all_params

    def select(self, *columns: str, append: bool = False) -> 'IQuery':
        """Select specific columns to retrieve from the query.

        Enhanced for CTE support to properly handle the special case of '*'
        and expressions.

        Args:
            *columns: Variable number of column names to select
            append: If True, append columns to existing selection.
                   If False (default), replace existing selection.

        Returns:
            IQuery: Query instance for method chaining
        """
        # Check if we have a star in current selection
        has_star = self.select_columns and "*" in self.select_columns

        # Call parent implementation
        result = super().select(*columns, append=append)

        # Handle special case for appending expressions to a SELECT *
        if append and has_star and columns and any("CASE" in col.upper() for col in columns):
            # If we're appending a CASE expression to a SELECT *,
            # ensure we keep the * in the selection
            if "*" not in self.select_columns:
                # Put * back at the beginning if it was removed
                self.select_columns.insert(0, "*")
                self._log(logging.DEBUG, "Preserved '*' selection when appending CASE expression")

        return result

    def _build_select(self) -> str:
        """Override _build_select to support CTEs as data sources.

        This method handles specialized SELECT clause building when using CTEs,
        with different behavior for aggregation and non-aggregation queries:

        1. For aggregation queries:
           - Include explicitly selected columns
           - Add all GROUP BY columns if not already selected
           - Add all expressions

        2. For non-aggregation queries:
           - Respect user's explicit column selection
           - If no explicit selection, default to SELECT *
           - Add expressions after selected columns

        Returns:
            SELECT clause with appropriate FROM reference
        """
        # If using a CTE as source, modify the FROM clause
        if self._cte_source:
            dialect = self.model_class.backend().dialect

            # Determine if this is an aggregate query
            is_aggregate = self._is_aggregate_query()

            # First prepare the column selection part
            select_parts = []

            # Track selected columns to avoid duplication
            selected_columns = set()

            # Check for explicit column selection
            has_explicit_selection = self.select_columns is not None
            has_star = has_explicit_selection and "*" in self.select_columns

            # Handle explicit selection
            if has_explicit_selection:
                for col in self.select_columns:
                    # Don't add * if we're in an aggregate query with expressions
                    # unless it's the only thing selected
                    if col == "*" and is_aggregate and self._expressions and len(self.select_columns) > 1:
                        continue

                    select_parts.append(col)

                    # Track column for deduplication (skip * as it's not a real column)
                    if col != "*":
                        # Extract column name for tracking (handle "column as alias" format)
                        base_col = col.split(' as ')[0].strip() if ' as ' in col else col
                        base_col = base_col.strip('"').strip('`')  # Remove quotes if present
                        selected_columns.add(base_col)

            # For aggregate queries: ensure we include all GROUP BY columns if not already selected
            if is_aggregate and hasattr(self, '_group_columns') and self._group_columns:
                for col in self._group_columns:
                    # Strip table qualifiers from group columns when using CTE
                    if '.' in col:
                        col = col.split('.')[-1]

                    # Only add if not already selected
                    if col not in selected_columns:
                        select_parts.append(dialect.format_identifier(col))
                        selected_columns.add(col)

            # Add all expressions
            if self._expressions:
                for expr in self._expressions:
                    select_parts.append(expr.as_sql())

            # If no columns selected at all, default to SELECT *
            if not select_parts:
                select_parts.append("*")

            # Build the SELECT clause
            select_part = f"SELECT {', '.join(select_parts)}"

            # Format the CTE reference
            cte_ref = self._cte_source
            if self._cte_alias:
                cte_ref = f"{self._cte_source} AS {self._cte_alias}"

            # Complete the FROM clause
            return f"{select_part} FROM {cte_ref}"

        # Otherwise use standard select
        return super()._build_select()

    def _process_cte_column_references(self, column: str) -> str:
        """Process column references when using CTE.

        When using a CTE, we need to handle column references differently,
        especially when they include table prefixes.

        Args:
            column: Column reference possibly with CTE prefix

        Returns:
            Processed column reference
        """
        if not self._cte_source:
            return column

        # If column already references the CTE (e.g., "tree.column"),
        # just return it as is
        cte_prefix = f"{self._cte_source}."
        alias_prefix = f"{self._cte_alias}." if self._cte_alias else ""

        # Column without any prefix
        if not column.startswith(cte_prefix) and not column.startswith(alias_prefix) and '.' not in column:
            return column

        # For "cte.*" patterns, return as is
        if column.endswith(".*"):
            return column

        # If prefixed with CTE name or alias, return as is
        if column.startswith(cte_prefix) or (alias_prefix and column.startswith(alias_prefix)):
            return column

        # Otherwise, column might be prefixed with original table name or another table,
        # for now, return as is
        return column

    def _build_group_by(self) -> Tuple[Optional[str], List[Any]]:
        """Build GROUP BY and HAVING clauses with special handling for CTEs.

        Returns:
            Tuple of (GROUP BY clause SQL, parameters)
        """
        # If this is aggregating from a CTE, need to use CTE column references
        if self._cte_source and self._group_columns:
            # For CTE sources, we don't need to qualify columns with table name
            query_parts = []
            params = []

            # Add GROUP BY with columns from the CTE
            group_columns = []
            for col in self._group_columns:
                # Strip table qualifiers from group columns when using CTE
                if '.' in col:
                    # Extract column name without table qualifier
                    col = col.split('.')[-1]
                group_columns.append(col)

            if group_columns:
                dialect = self.model_class.backend().dialect
                # Format identifiers to ensure proper quoting
                quoted_columns = [dialect.format_identifier(col) for col in group_columns]
                query_parts.append(f"GROUP BY {', '.join(quoted_columns)}")

            # Add HAVING conditions if any
            if self._having_conditions:
                having_parts = []
                for condition, condition_params in self._having_conditions:
                    having_parts.append(condition)
                    params.extend(condition_params)

                if having_parts:
                    query_parts.append(f"HAVING {' AND '.join(having_parts)}")

            if query_parts:
                return " ".join(query_parts), params
            return None, []

        # For non-CTE sources, use the parent implementation
        return super()._build_group_by()

    def _build_window_defs(self) -> Optional[str]:
        """Build WINDOW clause for named window definitions.

        Returns:
            Optional[str]: WINDOW clause or None if no definitions
        """
        if not self._window_definitions:
            return None

        window_parts = []

        for name, definition in self._window_definitions.items():
            window_spec = []

            if definition.get('partition_by'):
                window_spec.append(f"PARTITION BY {', '.join(definition['partition_by'])}")

            if definition.get('order_by'):
                window_spec.append(f"ORDER BY {', '.join(definition['order_by'])}")

            window_parts.append(f"{name} AS ({' '.join(window_spec)})")

        if window_parts:
            return f"WINDOW {', '.join(window_parts)}"

        return None

    def _build_sql_with_cte(self, include_cte: bool = True) -> Tuple[str, Tuple]:
        """Build complete SQL query with CTE support.

        This is a unified method for building SQL that handles:
        1. Common Table Expressions (CTEs)
        2. Aggregation (GROUP BY, HAVING, etc.)
        3. Special source from CTEs (from_cte)

        Args:
            include_cte: Whether to include CTE definitions in the query
                         (set to False when building subqueries)

        Returns:
            Tuple of (sql_query, params)
        """
        # First check if we need to add WITH clause
        with_clause, cte_params = None, []
        if include_cte and self._using_ctes and self._ctes:
            with_clause, cte_params = self._build_cte_clause()

        # Determine if we're doing an aggregate query
        is_aggregate = self._is_aggregate_query()

        # Build base query parts
        if is_aggregate:
            # Use AggregateQueryMixin's _build_aggregate_query but without CTE part
            base_sql, base_params = super()._build_aggregate_query()
        else:
            # Use standard build from parent
            base_sql, base_params = super().build()

        # If no WITH clause needed, return the base query
        if not with_clause:
            return base_sql, base_params

        # Combine WITH clause with main query
        full_sql = f"{with_clause} {base_sql}"
        all_params = tuple(list(cte_params) + list(base_params))

        self._log(logging.DEBUG, f"Generated SQL with CTEs: {full_sql}")
        return full_sql, all_params

    def _build_scalar_aggregate_query(self, func: str, column: str,
                                      distinct: bool = False) -> Tuple[str, tuple]:
        """Override base scalar aggregate query building to support CTEs.

        Ensures that scalar aggregate functions (COUNT, SUM, AVG, etc.) properly
        include CTE definitions when executed directly.

        Args:
            func: Aggregate function name (COUNT, SUM, etc.)
            column: Column to aggregate
            distinct: Whether to use DISTINCT

        Returns:
            Tuple of (sql_query, params)
        """
        # Clear any existing expressions
        self._expressions = []

        # Add single aggregate expression
        expr = AggregateExpression(func, column, distinct, "result")

        # Save original state and set new selection
        original_select = self.select_columns
        self.select_columns = [expr.as_sql()]

        # Build query with CTE support
        sql, params = self._build_sql_with_cte()

        # Restore original state
        self.select_columns = original_select

        return sql, params

    def build(self) -> Tuple[str, Tuple]:
        """Build complete SQL query with CTE support.

        This method extends the standard query building process to include
        Common Table Expressions (CTEs) if they have been defined.

        Returns:
            Tuple of (sql_query, params) where:
            - sql_query: SQL string with CTEs included
            - params: Tuple of parameter values including CTE parameters

        Examples:
            # Build a query with CTE
            sql, params = User.query()\\
                .with_cte("active_users", "SELECT * FROM users WHERE active = 1")\\
                .from_cte("active_users")\\
                .where("login_count > ?", (5,))\\
                .build()
        """
        return self._build_sql_with_cte()

    def _build_aggregate_query(self) -> Tuple[str, Tuple]:
        """Build complete aggregate query SQL and parameters.

        This method overrides AggregateQueryMixin's implementation to add CTE support.
        It delegates to _build_sql_with_cte for the actual query building.

        Returns:
            Tuple of (sql_query, params)
        """
        return self._build_sql_with_cte()

    def to_sql(self) -> Tuple[str, Tuple]:
        """Get complete SQL query with parameters including CTE support.

        This method returns the full SQL statement with parameter values
        ready for execution, including WITH clause if any CTEs are defined.

        Returns:
            Tuple of (sql_query, params) where:
            - sql_query: Complete SQL string with placeholders
            - params: Tuple of parameter values

        Examples:
            # Without CTE
            sql, params = User.query().where('status = ?', (1,)).to_sql()
            print(f"SQL: {sql}")
            print(f"Params: {params}")

            # With CTE
            sql, params = User.query()\\
                .with_cte("active_users", "SELECT * FROM users WHERE status = 'active'")\\
                .from_cte("active_users")\\
                .where("login_count > ?", (5,))\\
                .to_sql()
        """
        # Simply delegate to build() and log the result
        sql, params = self.build()
        self._log(logging.DEBUG, f"Generated SQL: {sql}")
        self._log(logging.DEBUG, f"SQL parameters: {params}")
        return sql, params

    # The following methods are kept for documentation purposes
    # They simply call the parent implementation

    def all(self) -> List[ModelT]:
        """Execute query and return all matching records.

        This method executes the query including any defined CTEs and returns
        a list of model instances representing all matching records. The
        returned list will be empty if no records match the query conditions.

        If explain() has been called on the query, this method will return
        the execution plan instead of the actual results. The format of the
        plan depends on the options provided to explain().

        If eager loading is configured via with_(), related records will be
        loaded and associated with the returned models (only applies when
        not in explain mode).

        Returns:
            List[ModelT]: List of model instances (empty if no matches)
            Union[str, List[Dict]]: Execution plan if explain is enabled

        Examples:
            # Normal execution
            users = User.query().where('status = ?', ('active',)).all()

            # With CTE
            users = User.query()\\
                .with_cte("active_users", "SELECT * FROM users WHERE status = 'active'")\\
                .from_cte("active_users")\\
                .all()

            # With execution plan
            plan = User.query()\\
                .explain()\\
                .with_cte("active_users", "SELECT * FROM users WHERE status = 'active'")\\
                .from_cte("active_users")\\
                .all()

            # With eager loading (normal execution)
            users = User.query()\\
                .with_('posts', 'profile')\\
                .where('created_at >= ?', (last_week,))\\
                .all()
        """
        return super().all()

    def one(self) -> Optional[ModelT]:
        """Execute query and return the first matching record.

        This method executes the query with a LIMIT 1 clause and returns either:
        - A single model instance if a matching record is found
        - None if no matching records exist
        - Execution plan if explain() has been called on the query

        The method preserves any existing LIMIT clause after execution.

        Returns:
            Optional[ModelT]: Single model instance or None
            Union[str, List[Dict]]: Execution plan if explain is enabled

        Examples:
            # Normal execution
            user = User.query().where('email = ?', (email,)).one()

            # With CTE
            user = User.query()\\
                .with_cte("active_admins", "SELECT * FROM users WHERE status = 'active' AND role = 'admin'")\\
                .from_cte("active_admins")\\
                .one()

            # With execution plan
            plan = User.query()\\
                .explain(explain_type='ANALYZE')\\
                .where('email = ?', (email,))\\
                .one()

            # Handle potential None result (normal execution)
            if (user := User.query().where('email = ?', (email,)).one()):
                print(f"Found user: {user.name}")
            else:
                print("User not found")
        """
        return super().one()

    def aggregate(self) -> List[Dict[str, Any]]:
        """Execute aggregate query with all configured expressions and groupings.

        Executes the query with all configured expressions and groupings.
        Inherits WHERE conditions, ORDER BY, and LIMIT/OFFSET from base query.

        Returns a list of result dictionaries. The list may contain a single item
        or multiple items depending on the query definition (GROUP BY, etc.).

        If explain() has been called on the query, this method will return
        the execution plan instead of the actual results.

        Returns:
            List[Dict[str, Any]]: Results as a list of dictionaries
            Union[str, List[Dict]]: Execution plan if explain is enabled

        Examples:
            # With grouping (returns multiple rows)
            result = User.query()\\
                .group_by('department')\\
                .count('id', 'total')\\
                .aggregate()

            # Scalar aggregate (returns a single row in a list)
            result = User.query()\\
                .count('id', 'total')\\
                .aggregate()
            total = result[0]['total'] if result else 0

            # With CTE
            result = User.query()\\
                .with_cte("active_users", "SELECT * FROM users WHERE status = 'active'")\\
                .from_cte("active_users")\\
                .group_by('department')\\
                .count('id', 'total')\\
                .aggregate()
        """
        return super().aggregate()

    def to_dict(self, include: Optional[Set[str]] = None, exclude: Optional[Set[str]] = None,
                direct_dict: bool = False) -> 'DictQuery':
        """Convert query results to dictionary format.

        This method provides two approaches to dictionary conversion:

        1. Standard mode (default): First instantiates model objects (with validation),
           then converts them to dictionaries

        2. Direct dictionary mode: Bypasses model instantiation entirely and returns
           raw dictionaries from the database. This is useful for JOIN queries or
           when the result set contains columns not defined in the model.

        Works with CTEs as data sources, just like all() and one() methods.

        Args:
            include: Optional set of fields to include in results
            exclude: Optional set of fields to exclude from results
            direct_dict: If True, bypasses model instantiation entirely and returns
                         raw dictionaries from the database

        Returns:
            DictQuery: A query wrapper that returns dictionary results

        Examples:
            # Standard usage - models are instantiated first
            users = User.query().to_dict().all()

            # With CTE
            results = User.query()\\
                .with_cte("active_users", "SELECT * FROM users WHERE status = 'active'")\\
                .from_cte("active_users")\\
                .to_dict()\\
                .all()

            # For JOIN queries - bypass model instantiation
            results = User.query()\\
                .join("JOIN orders ON users.id = orders.user_id")\\
                .select("users.id", "users.name", "orders.total")\\
                .to_dict(direct_dict=True)\\
                .all()

            # Including only specific fields
            users = User.query()\\
                .to_dict(include={'id', 'name', 'email'})\\
                .all()

            # Excluding specific fields
            users = User.query()\\
                .to_dict(exclude={'password', 'secret_token'})\\
                .all()
        """
        return super().to_dict(include, exclude, direct_dict)

    def count(self, column: str = "*", alias: Optional[str] = None,
              distinct: bool = False) -> Union['CTEQueryMixin', int]:
        """Add COUNT expression or execute scalar count.

        This method has two behaviors:
        1. When used in aggregate query (with GROUP BY or other aggregates):
           Returns query instance with COUNT expression added
        2. When used alone:
           - In normal mode: Executes COUNT immediately and returns the result
           - In explain mode: Returns the execution plan for the COUNT query

        CTE Support:
           When used with CTEs, the COUNT operation will properly include the CTE
           definitions in the query.

        Args:
            column: Column to count
            alias: Optional alias for grouped results
            distinct: Whether to count distinct values

        Returns:
            Query instance for chaining if in aggregate query
            Count result if scalar count
            Execution plan if explain is enabled

        Examples:
            # Simple count (immediate execution)
            total = User.query().count()

            # With CTE
            total = User.query()\\
                .with_cte("active_users", "SELECT * FROM users WHERE status = 'active'")\\
                .from_cte("active_users")\\
                .count()

            # With execution plan
            plan = User.query()\\
                .explain()\\
                .count()

            # As part of aggregate query
            result = User.query()\\
                .group_by('type')\\
                .count('id', 'total')\\
                .explain()\\
                .aggregate()
        """
        return super().count(column, alias, distinct)

    def sum(self, column: str, alias: Optional[str] = None) -> Union['CTEQueryMixin', Optional[Union[int, float]]]:
        """Add SUM expression or execute scalar sum.

        CTE Support:
           When used with CTEs, the SUM operation will properly include the CTE
           definitions in the query.

        Args:
            column: Column to sum
            alias: Optional alias for grouped results

        Returns:
            Query instance for chaining if in aggregate query
            Sum result if scalar sum
            Execution plan if explain is enabled

        Examples:
            # Simple sum
            total = User.query().sum('balance')

            # With CTE
            total = User.query()\\
                .with_cte("premium_users", "SELECT * FROM users WHERE type = 'premium'")\\
                .from_cte("premium_users")\\
                .sum('balance')
        """
        return super().sum(column, alias)

    def avg(self, column: str, alias: Optional[str] = None) -> Union['CTEQueryMixin', Optional[float]]:
        """Add AVG expression or execute scalar average.

        CTE Support:
           When used with CTEs, the AVG operation will properly include the CTE
           definitions in the query.

        Args:
            column: Column to average
            alias: Optional alias for grouped results

        Returns:
            Query instance for chaining if in aggregate query
            Average result if scalar average
            Execution plan if explain is enabled

        Examples:
            # Simple average
            avg_balance = User.query().avg('balance')

            # With CTE
            avg_balance = User.query()\\
                .with_cte("premium_users", "SELECT * FROM users WHERE type = 'premium'")\\
                .from_cte("premium_users")\\
                .avg('balance')
        """
        return super().avg(column, alias)

    def min(self, column: str, alias: Optional[str] = None) -> Union['CTEQueryMixin', Optional[Any]]:
        """Add MIN expression or execute scalar min.

        CTE Support:
           When used with CTEs, the MIN operation will properly include the CTE
           definitions in the query.

        Args:
            column: Column to find minimum
            alias: Optional alias for grouped results

        Returns:
            Query instance for chaining if in aggregate query
            Minimum result if scalar min
            Execution plan if explain is enabled

        Examples:
            # Simple minimum
            min_balance = User.query().min('balance')

            # With CTE
            min_balance = User.query()\\
                .with_cte("premium_users", "SELECT * FROM users WHERE type = 'premium'")\\
                .from_cte("premium_users")\\
                .min('balance')
        """
        return super().min(column, alias)

    def max(self, column: str, alias: Optional[str] = None) -> Union['CTEQueryMixin', Optional[Any]]:
        """Add MAX expression or execute scalar max.

        CTE Support:
           When used with CTEs, the MAX operation will properly include the CTE
           definitions in the query.

        Args:
            column: Column to find maximum
            alias: Optional alias for grouped results

        Returns:
            Query instance for chaining if in aggregate query
            Maximum result if scalar max
            Execution plan if explain is enabled

        Examples:
            # Simple maximum
            max_balance = User.query().max('balance')

            # With CTE
            max_balance = User.query()\\
                .with_cte("premium_users", "SELECT * FROM users WHERE type = 'premium'")\\
                .from_cte("premium_users")\\
                .max('balance')
        """
        return super().max(column, alias)

    def __copy__(self):
        """Implement shallow copy protocol for CTE queries.

        Extends the AggregateQueryMixin.__copy__ implementation to include
        CTE-specific properties.

        Returns:
            A new instance of the CTE query with properties copied.
        """
        # Start with the base copy
        result = super().__copy__()

        # Copy CTE-specific properties
        # For simple shallow copy, we just copy the dictionaries and properties
        if hasattr(self, '_ctes'):
            result._ctes = self._ctes.copy() if self._ctes else {}
        else:
            result._ctes = {}

        if hasattr(self, '_using_ctes'):
            result._using_ctes = self._using_ctes
        else:
            result._using_ctes = False

        if hasattr(self, '_cte_source'):
            result._cte_source = self._cte_source
        else:
            result._cte_source = None

        if hasattr(self, '_cte_alias'):
            result._cte_alias = self._cte_alias
        else:
            result._cte_alias = None

        if hasattr(self, '_from_clause'):
            result._from_clause = self._from_clause
        else:
            result._from_clause = None

        return result

    def __deepcopy__(self, memo):
        """Implement deep copy protocol for CTE queries.

        Extends the AggregateQueryMixin.__deepcopy__ implementation to ensure
        all CTE-specific nested objects are also deeply copied.

        Args:
            memo: Dictionary of already copied objects to avoid infinite recursion

        Returns:
            A completely independent copy of the CTE query
        """
        import copy

        # If this object has already been copied, return the copy
        if id(self) in memo:
            return memo[id(self)]

        # Start with a shallow copy
        result = self.__copy__()

        # Track the copied object to avoid infinite recursion
        memo[id(self)] = result

        # Call parent's __deepcopy__ to handle base and aggregate properties
        super().__deepcopy__(memo)

        # Deep copy the CTE definitions, which may contain complex objects
        if hasattr(self, '_ctes') and self._ctes:
            result._ctes = copy.deepcopy(self._ctes, memo)

        return result
