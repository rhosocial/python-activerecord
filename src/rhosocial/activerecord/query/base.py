"""Base query mixin implementation."""
import logging
from typing import List, Any, Optional, Union, Set, Tuple, Dict

from .dict_query import DictQuery
from ..backend.dialect import ExplainType, ExplainOptions, ExplainFormat
from ..backend.errors import QueryError, RecordNotFound
from ..interface import ModelT, IQuery


class BaseQueryMixin(IQuery[ModelT]):
    """Base implementation of query building interface.

    Provides methods for:
    - WHERE conditions
    - ORDER BY
    - GROUP BY
    - LIMIT/OFFSET
    - Query execution
    """

    def _log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Log query-related messages using model's logger."""
        if self.model_class:
            if "offset" not in kwargs:
                kwargs["offset"] = 1
            self.model_class.log(level, msg, *args, **kwargs)

    def to_sql(self) -> Tuple[str, tuple]:
        """Get SQL statement and its parameters."""
        sql, params = self.build()
        self._log(logging.DEBUG, f"Generated SQL: {sql}, parameters: {params}")
        return sql, params

    def explain(self,
                type: Optional[ExplainType] = None,
                format: ExplainFormat = ExplainFormat.TEXT,
                **kwargs) -> 'IQuery[ModelT]':
        """Enable EXPLAIN for the subsequent query execution.

        This method configures the query to generate an execution plan when executed.
        The `explain` will be performed when calling execution methods like all(), one(),
        count(), etc.

        Args:
            type: Type of explain output
            format: Output format (TEXT/JSON/XML/YAML)
            **kwargs: Additional EXPLAIN options:
                costs (bool): Show estimated costs
                buffers (bool): Show buffer usage
                timing (bool): Include timing information
                verbose (bool): Show additional information
                settings (bool): Show modified settings (PostgreSQL)
                wal (bool): Show WAL usage (PostgreSQL)

        Returns:
            IQuery[ModelT]: Query instance for method chaining

        Examples:
            # Basic explain
            User.query().explain().all()

            # With analysis and JSON output
            User.query()\\
                .explain(type=ExplainType.ANALYZE, format=ExplainFormat.JSON)\\
                .all()

            # PostgreSQL specific options
            User.query()\\
                .explain(buffers=True, settings=True)\\
                .all()

            # Configure explain for aggregate query
            plan = User.query()\\
                .group_by('department')\\
                .explain(format=ExplainFormat.TEXT)\\
                .count('id', 'total')

            # Explain can be called at any point before execution
            query = User.query().where('active = ?', (True,))
            query.explain()  # Enable explain
            result = query.all()  # Will show execution plan
        """
        self._explain_enabled = True
        self._explain_options = ExplainOptions(
            type=type or ExplainType.BASIC,
            format=format,
            **kwargs
        )
        return self

    def _execute_with_explain(self, sql: str, params: tuple) -> Union[str, List[Dict]]:
        """Execute SQL with EXPLAIN if enabled.

        Internal method to handle EXPLAIN execution. Used by execution methods
        like all(), one(), count() etc.

        Args:
            sql: SQL to execute/explain
            params: Query parameters

        Returns:
            Union[str, List[Dict]]: Execution plan if explain is enabled,
                                  otherwise executes the query normally
        """
        backend = self.model_class.backend()
        if not self._explain_enabled:
            self._log(logging.DEBUG, "explain not enabled")
            return backend.execute(sql, params, returning=True)

        # Validate options for current database
        self._explain_options.validate_for_database(backend.dialect.__class__.__name__)

        # Build explain SQL using dialect
        explain_sql = backend.dialect.format_explain(sql, self._explain_options)

        # Execute explain
        self._log(logging.INFO, f"Executing query: {explain_sql}, parameters: {params}")
        result = backend.execute(explain_sql, params, returning=True)

        # Return raw data for non-text formats
        if self._explain_options.format != ExplainFormat.TEXT:
            return result.data

        self._log(logging.DEBUG, f"Explained: {result}")

        # Format text output
        return "\n".join(str(row) for row in result.data)

    def select(self, *columns: str) -> 'IQuery':
        """Select specific columns to retrieve from the query.

        This method allows you to specify which columns should be included in the query results.
        If no columns are specified, all columns (*) will be selected.

        Args:
            *columns: Variable number of column names to select

        Returns:
            IQuery: Query instance for method chaining

        Examples:
            # Select specific columns
            User.query().select('id', 'name', 'email')

            # Select all columns (default behavior)
            User.query().select()

            # Select with table alias
            User.query().select('users.id', 'users.name')
        """
        self.select_columns = list(columns) if columns else ["*"]
        self._log(logging.DEBUG, f"Set select columns: {self.select_columns}")
        return self

    def query(self, conditions: Optional[Dict[str, Any]] = None) -> 'IQuery[ModelT]':
        """Configure query with given conditions.

        This method provides a convenient way to add multiple query conditions
        from a dictionary. The keys in the conditions dictionary can be:
        - Simple column names: Will generate "column = ?" conditions
        - Column names with operators: Will use the specified operator
        - Special keys starting with "_": Reserved for future query options

        The method handles different value types appropriately:
        - None: Generates IS NULL condition
        - List/Tuple: Generates IN condition
        - Other values: Generates basic equality condition

        Args:
            conditions: Dictionary of conditions where:
                - Keys are column names (optionally with operators)
                - Values are the condition values

        Returns:
            IQuery[ModelT]: Query instance with conditions applied

        Examples:
            # Simple equality conditions
            query.query({
                'status': 'active',
                'type': 'user'
            })
            # WHERE status = ? AND type = ?

            # Using operators
            query.query({
                'age__gt': 18,
                'name__like': 'John%'
            })
            # WHERE age > ? AND name LIKE ?

            # NULL conditions
            query.query({
                'deleted_at': None
            })
            # WHERE deleted_at IS NULL

            # IN conditions
            query.query({
                'status': ['active', 'pending']
            })
            # WHERE status IN (?, ?)

            # Combined conditions
            query.query({
                'type': 'user',
                'age__gte': 18,
                'status': ['active', 'pending'],
                'deleted_at': None
            })
            # WHERE type = ? AND age >= ? AND status IN (?, ?) AND deleted_at IS NULL
        """
        if not conditions:
            return self

        self._log(logging.DEBUG, f"Processing query conditions: {conditions}")

        operator_map = {
            'gt': '>',
            'lt': '<',
            'gte': '>=',
            'lte': '<=',
            'ne': '!=',
            'like': 'LIKE',
            'not_like': 'NOT LIKE',
            'in': 'IN',
            'not_in': 'NOT IN'
        }

        for key, value in conditions.items():
            # Skip special configuration keys starting with '_'
            if key.startswith('_'):
                self._log(logging.DEBUG, f"Skipping special key: {key}")
                continue

            # Parse key to get column and operator
            parts = key.split('__')
            column = parts[0]
            op = parts[1] if len(parts) > 1 else None

            # Handle different value types and operators
            if value is None:
                self.where(f"{column} IS NULL")

            elif isinstance(value, (list, tuple)):
                if not value:  # Empty list
                    continue
                placeholders = ','.join(['?' for _ in value])
                self.where(f"{column} IN ({placeholders})", value)

            elif op and op in operator_map:
                operator = operator_map[op]
                if operator in ('IN', 'NOT IN'):
                    if not isinstance(value, (list, tuple)):
                        value = [value]
                    placeholders = ','.join(['?' for _ in value])
                    self.where(f"{column} {operator} ({placeholders})", value)
                else:
                    self.where(f"{column} {operator} ?", (value,))

            else:
                # Default to equality comparison
                self.where(f"{column} = ?", (value,))

        return self

    def where(self, condition: str, params: Optional[Union[tuple, List[Any]]] = None) -> 'IQuery':
        """Add AND condition.

        Args:
            condition: Condition expression
            params: Condition parameters

        Returns:
            Query instance

        Example:
            query.where('status = ?', (1,))
        """
        if params is None:
            params = tuple()
        elif not isinstance(params, tuple):
            params = tuple(params)

        self.condition_groups[self.current_group].append((condition, params, 'AND'))
        self._log(logging.DEBUG, f"Added WHERE condition: {condition}, parameters: {params}")
        return self

    def or_where(self, condition: str, params: Optional[Union[tuple, List[Any]]] = None) -> 'IQuery[ModelT]':
        """Add OR condition.

        Args:
            condition: Condition expression
            params: Condition parameters

        Returns:
            Query instance

        Example:
            # Basic OR condition
            query.where('status = ?', (1,))\\
                .or_where('status = ?', (2,))

            # Equivalent to: WHERE status = 1 OR status = 2

            # Complex condition combination
            query.where('status = ?', (1,))\\
                .or_where('type = ?', ('admin',))\\
                .where('deleted_at IS NULL')

            # Equivalent to: WHERE (status = 1 OR type = 'admin') AND deleted_at IS NULL
        """
        if params is None:
            params = tuple()
        elif not isinstance(params, tuple):
            params = tuple(params)

        self.condition_groups[self.current_group].append((condition, params, 'OR'))
        self._log(logging.DEBUG, f"Added OR WHERE condition: {condition}, parameters: {params}")
        return self

    def start_or_group(self) -> 'IQuery[ModelT]':
        """Start a new OR condition group.

        New conditions within the group will be wrapped in parentheses.

        Example:
            query.where('status = ?', (1,))\\
                .start_or_group()\\
                .where('type = ?', ('admin',))\\
                .or_where('type = ?', ('staff',))\\
                .end_or_group()

            # Equivalent to: WHERE status = 1 AND (type = 'admin' OR type = 'staff')
        """
        self.condition_groups.append([])
        self.current_group = len(self.condition_groups) - 1
        self._log(logging.DEBUG, "Started new OR condition group")
        return self

    def end_or_group(self) -> 'IQuery[ModelT]':
        """End current OR condition group."""
        if self.current_group > 0:
            self.current_group = 0
            self._log(logging.DEBUG, "Ended OR condition group")
        return self

    def order_by(self, *clauses: str) -> 'IQuery':
        """Add ORDER BY clauses."""
        self.order_clauses.extend(clauses)
        self._log(logging.DEBUG, f"Added ORDER BY clauses: {clauses}")
        return self

    def join(self, join_clause: str) -> 'IQuery':
        """Add JOIN clause."""
        self.join_clauses.append(join_clause)
        self._log(logging.DEBUG, f"Added JOIN clause: {join_clause}")
        return self

    def limit(self, count: int) -> 'IQuery':
        """Set LIMIT."""
        if count < 0:
            self._log(logging.ERROR, f"Invalid negative limit count: {count}")
            raise QueryError("Limit count must be non-negative")
        self.limit_count = count
        self._log(logging.DEBUG, f"Set LIMIT to {count}")
        return self

    def offset(self, count: int) -> 'IQuery':
        """Set OFFSET."""
        if count < 0:
            self._log(logging.ERROR, f"Invalid negative offset count: {count}", offset=2)
            raise QueryError("Offset count must be non-negative")
        if self.limit_count is None:
            self._log(logging.WARNING,
                     "Using OFFSET without LIMIT may be unsupported by some databases")
        self.offset_count = count
        self._log(logging.DEBUG, f"Set OFFSET to {count}")
        return self

    def _build_select(self) -> str:
        """Build SELECT and FROM clauses."""
        dialect = self.model_class.backend().dialect
        table = dialect.format_identifier(self.model_class.table_name())
        return f"SELECT {', '.join(self.select_columns)} FROM {table}"

    def _build_joins(self) -> List[str]:
        """Build JOIN clauses."""
        return self.join_clauses.copy() if self.join_clauses else []

    def _build_where(self) -> Tuple[Optional[str], List[Any]]:
        """Build WHERE clause and collect parameters."""
        params = []
        where_parts = []

        for i, group in enumerate(self.condition_groups):
            if not group:
                continue

            group_clauses = []
            for j, (condition, condition_params, operator) in enumerate(group):
                if j == 0:
                    group_clauses.append(condition)
                else:
                    group_clauses.append(f"{operator} {condition}")
                params.extend(condition_params)

            if group_clauses:
                group_sql = ' '.join(group_clauses)
                if i > 0 or any(op == 'OR' for _, _, op in group):
                    group_sql = f"({group_sql})"
                where_parts.append(group_sql)

        if where_parts:
            return f"WHERE {' AND '.join(where_parts)}", params
        return None, params

    def _build_order(self) -> Optional[str]:
        """Build ORDER BY clause."""
        if self.order_clauses:
            return f"ORDER BY {', '.join(self.order_clauses)}"
        return None

    def _build_limit_offset(self) -> Optional[str]:
        """Build LIMIT/OFFSET clause using dialect."""
        dialect = self.model_class.backend().dialect
        return dialect.format_limit_offset(self.limit_count, self.offset_count)

    def build(self) -> Tuple[str, tuple]:
        """Build complete SQL query with parameters.

        Returns:
            Tuple of (sql_query, params) where:
            - sql_query: Complete SQL string with placeholders
            - params: Tuple of parameter values

        Raises:
            QueryError: If query construction fails
        """
        query_parts = [self._build_select()]
        all_params = []

        # Add JOIN clauses
        join_parts = self._build_joins()
        if join_parts:
            query_parts.extend(join_parts)

        # Add WHERE clause
        where_sql, where_params = self._build_where()
        if where_sql:
            query_parts.append(where_sql)
            all_params.extend(where_params)

        # Add ORDER BY clause
        order_sql = self._build_order()
        if order_sql:
            query_parts.append(order_sql)

        # Add LIMIT/OFFSET clause
        limit_offset_sql = self._build_limit_offset()
        if limit_offset_sql:
            query_parts.append(limit_offset_sql)

        return " ".join(query_parts), tuple(all_params)

    def all(self) -> List[ModelT]:
        """Execute query and return all matching records.

        This method executes the query and returns a list of model instances
        representing all matching records. The returned list will be empty if
        no records match the query conditions.

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

            # With execution plan
            plan = User.query()\\
                .explain()\\
                .where('status = ?', ('active',))\\
                .all()

            # With eager loading (normal execution)
            users = User.query()\\
                .with_('posts', 'profile')\\
                .where('created_at >= ?', (last_week,))\\
                .all()
        """
        sql, params = self.build()

        # Handle explain if enabled
        if self._explain_enabled:
            return self._execute_with_explain(sql, params)

        self._log(logging.INFO, f"Executing query: {sql}, parameters: {params}")

        rows = self.model_class.backend().fetch_all(sql, params)
        records = self.model_class.create_collection_from_database(rows)

        if self._eager_loads:
            self._log(logging.DEBUG, f"Loading eager relations: {list(self._eager_loads.keys())}")
            self._load_relations(records)

        return records

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
        original_limit = self.limit_count
        self.limit(1)

        sql, params = self.build()

        # Handle explain if enabled
        if self._explain_enabled:
            return self._execute_with_explain(sql, params)

        self._log(logging.INFO, f"Executing query: {sql}, parameters: {params}")

        row = self.model_class.backend().fetch_one(sql, params, self.model_class.model_construct().column_types())

        self.limit_count = original_limit

        if not row:
            return None

        record = self.model_class.create_from_database(row)

        if self._eager_loads:
            # self._log(logging.INFO, f"Loading eager relations: {list(self._eager_loads.keys())}...")
            self._load_relations([record])

        return record

    def one_or_fail(self) -> ModelT:
        """Get single record, raise exception if not found.

        Similar to one(), but raises an exception if no record is found.
        If explain() has been called, returns the execution plan instead
        of attempting to find a record.

        Returns:
            ModelT: Found record
            Union[str, List[Dict]]: Execution plan if explain is enabled

        Raises:
            RecordNotFound: When record is not found (only in normal execution mode)

        Examples:
            # Normal execution
            user = User.query().where('id = ?', (user_id,)).one_or_fail()

            # With execution plan
            plan = User.query()\\
                .explain()\\
                .where('id = ?', (user_id,))\\
                .one_or_fail()
        """
        record = self.one()
        if record is None:
            sql, params = self.build()
            self._log(
                logging.WARNING,
                f"Record not found for {self.model_class.__name__}: {sql} with params {params}"
            )
            raise RecordNotFound(f"Record not found for {self.model_class.__name__}")
        return record

    def count(self) -> Union[int, str, List[Dict]]:
        """Get the total number of records matching the query conditions.

        This method modifies the query to use COUNT(*) and executes it to determine
        the total number of matching records. It preserves the original SELECT columns
        after execution.

        If explain() has been called on the query, this method will return
        the execution plan for the COUNT query instead of the actual count.

        Returns:
            int: Number of matching records
            Union[str, List[Dict]]: Execution plan if explain is enabled

        Examples:
            # Normal count
            total = User.query().count()

            # With execution plan
            plan = User.query()\\
                .explain()\\
                .where('active = ?', (True,))\\
                .count()

            # Count with conditions (normal execution)
            active_count = User.query()\\
                .where('status = ?', ('active',))\\
                .count()
        """
        original_select = self.select_columns
        self.select_columns = ["COUNT(*) as count"]
        sql, params = self.build()
        self.select_columns = original_select

        # Handle explain if enabled
        if self._explain_enabled:
            return self._execute_with_explain(sql, params)

        self._log(logging.INFO, f"Executing count query: {sql}, parameters: {params}")
        result = self.model_class.backend().fetch_one(sql, params)
        return result["count"] if result else 0

    def exists(self) -> bool:
        """Check if any matching records exist."""
        return self.count() > 0

    def to_dict(self, include: Optional[Set[str]] = None, exclude: Optional[Set[str]] = None) -> 'DictQuery':
        """Convert to dictionary query."""
        from .dict_query import DictQuery
        return DictQuery(self, include, exclude)