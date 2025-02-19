"""Base query mixin implementation."""
import logging
from typing import List, Any, Optional, Union, Set, Tuple, Dict

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
        if self.model_class.__logger__:
            self.model_class.__logger__.log(level, msg, *args, **kwargs)

    def to_sql(self) -> Tuple[str, tuple]:
        """Get SQL statement and its parameters."""
        sql, params = self.build()
        self._log(logging.DEBUG, f"Generated SQL: {sql}")
        self._log(logging.DEBUG, f"SQL parameters: {params}")
        return sql, params

    def explain(self) -> str:
        """Get query execution plan."""
        sql, params = self.build()
        explain_sql = f"EXPLAIN QUERY PLAN {sql}"
        self._log(logging.DEBUG, f"Executing EXPLAIN: {explain_sql}")

        cursor = self.model_class.backend().execute(explain_sql, params)
        return "\n".join(str(row) for row in cursor.fetchall())

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
        self._log(logging.DEBUG, f"Added WHERE condition: {condition}")
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
        return self

    def end_or_group(self) -> 'IQuery[ModelT]':
        """End current OR condition group."""
        if self.current_group > 0:
            self.current_group = 0
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
            raise QueryError("Limit count must be non-negative")
        self.limit_count = count
        self._log(logging.DEBUG, f"Set LIMIT to {count}")
        return self

    def offset(self, count: int) -> 'IQuery':
        """Set OFFSET."""
        if count < 0:
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

        If eager loading is configured via with_(), related records will be
        loaded and associated with the returned models.

        Returns:
            List[ModelT]: List of model instances (empty if no matches)

        Examples:
            # Get all active users
            users = User.query().where('status = ?', ('active',)).all()

            # Get users with eager loaded relations
            users = User.query()\\
                .with_('posts', 'profile')\\
                .where('created_at >= ?', (last_week,))\\
                .all()

            # Process all matching records
            for user in User.query().where('needs_update = ?', (True,)).all():
                user.update_data()
        """
        sql, params = self.build()
        self._log(logging.INFO, f"Executing query: {sql}")
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

        The method preserves any existing LIMIT clause after execution.

        Returns:
            Optional[ModelT]: Single model instance or None

        Examples:
            # Find first active user
            user = User.query().where('status = ?', ('active',)).one()

            # Find oldest user
            user = User.query().order_by('created_at ASC').one()

            # Handle potential None result
            if (user := User.query().where('email = ?', (email,)).one()):
                print(f"Found user: {user.name}")
            else:
                print("User not found")
        """
        original_limit = self.limit_count
        self.limit(1)

        sql, params = self.build()
        self._log(logging.INFO, f"Executing query: {sql}")
        row = self.model_class.backend().fetch_one(sql, params, self.model_class.model_construct().column_types())

        self.limit_count = original_limit

        if not row:
            return None

        record = self.model_class.create_from_database(row)

        if self._eager_loads:
            self._log(logging.DEBUG, f"Loading eager relations: {list(self._eager_loads.keys())}")
            self._load_relations([record])

        return record

    def one_or_fail(self) -> ModelT:
        """Get single record, raise exception if not found.

        Returns:
            ModelT: Found record

        Raises:
            RecordNotFound: When record is not found
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

    def count(self) -> int:
        """Get the total number of records matching the query conditions.

        This method modifies the query to use COUNT(*) and executes it to determine
        the total number of matching records. It preserves the original SELECT columns
        after execution.

        Returns:
            int: Number of matching records

        Examples:
            # Count all users
            total = User.query().count()

            # Count active users
            active_count = User.query().where('status = ?', ('active',)).count()

            # Count users by type
            admin_count = User.query().where('type = ?', ('admin',)).count()
        """
        original_select = self.select_columns
        self.select_columns = ["COUNT(*) as count"]
        sql, params = self.build()
        self.select_columns = original_select

        self._log(logging.INFO, f"Executing count query: {sql}")
        result = self.model_class.backend().fetch_one(sql, params)
        return result["count"] if result else 0

    def exists(self) -> bool:
        """Check if any matching records exist."""
        return self.count() > 0

    def to_dict(self, include: Optional[Set[str]] = None, exclude: Optional[Set[str]] = None) -> 'DictQuery':
        """Convert to dictionary query."""
        from .dict_query import DictQuery
        return DictQuery(self, include, exclude)