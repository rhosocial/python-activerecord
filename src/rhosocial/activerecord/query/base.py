# src/rhosocial/activerecord/query/base.py
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

    def _format_identifier(self, identifier: str, dialect=None) -> str:
        """Format a column or table identifier according to database dialect rules.

        This method properly handles:
        - Simple identifiers (e.g., "name")
        - Table-qualified identifiers (e.g., "users.name")
        - Aliases (e.g., "name AS display_name")
        - Already quoted identifiers (preserves them)

        Args:
            identifier: The identifier to format
            dialect: Optional dialect to use (defaults to model's dialect)

        Returns:
            Properly formatted and quoted identifier
        """
        if not dialect:
            dialect = self.model_class.backend().dialect

        # If the identifier contains function calls, subqueries, or is already quoted
        # or contains an alias definition, return it as is
        if any(token in identifier for token in ['(', ')', ' as ', ' AS ', '"', '`', "'", '*']):
            return identifier

        # Check if this is a column with table qualification
        parts = identifier.split('.')
        if len(parts) == 2:
            # Handle "table.column" format
            table, column = parts
            return f"{dialect.format_identifier(table)}.{dialect.format_identifier(column)}"

        # Simple identifier
        return dialect.format_identifier(identifier)

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

    def select(self, *columns: str, append: bool = False) -> 'IQuery':
        """Select specific columns to retrieve from the query.

        This method allows you to specify which columns should be included in the query results.
        If no columns are specified, all columns (*) will be selected.

        By default, each call to select() replaces previously selected columns.
        If append=True is specified, new columns will be added to the existing selection.

        Args:
            *columns: Variable number of column names to select
            append: If True, append columns to existing selection.
                   If False (default), replace existing selection.

        Returns:
            IQuery: Query instance for method chaining

        Examples:
            # Select specific columns
            User.query().select('id', 'name', 'email')

            # Select all columns (default behavior)
            User.query().select()

            # Select with table alias
            User.query().select('users.id', 'users.name')

            # Replace previous selection
            query = User.query().select('id', 'name')
            query.select('email')  # Only 'email' will be selected

            # Append to previous selection
            query = User.query().select('id', 'name')
            query.select('email', append=True)  # 'id', 'name', and 'email' will be selected

            # Build complex queries incrementally
            query = Order.query()
                .select('id', 'status')
                .select('SUM(amount) as total', append=True)
        """
        if append:
            if not hasattr(self, 'select_columns') or self.select_columns is None:
                self.select_columns = []
            self.select_columns.extend(columns)
            self._log(logging.DEBUG, f"Added columns to SELECT: {columns}")
        else:
            self.select_columns = list(columns) if columns else None
            self._log(logging.DEBUG, f"Set SELECT columns to: {columns}")

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
            params = ()
        elif not isinstance(params, tuple):
            try:
                params = tuple(params)
            except TypeError:
                self._log(logging.ERROR, "Invalid params type for condition: %s", condition)
                raise QueryError("Did you forget to pass scalar values in a tuple?") from None

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
            params = ()
        elif not isinstance(params, tuple):
            try:
                params = tuple(params)
            except TypeError:
                self._log(logging.ERROR, "Invalid params type for condition: %s", condition)
                raise QueryError("Did you forget to pass scalar values in a tuple?") from None

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
        """Build SELECT and FROM clauses with proper dialect quoting."""
        dialect = self.model_class.backend().dialect
        table = dialect.format_identifier(self.model_class.table_name())

        # If select_columns is None, select all columns
        if self.select_columns is None:
            return f"SELECT * FROM {table}"

        # Format each column identifier
        formatted_columns = []
        for col in self.select_columns:
            # Handle special case for COUNT(*) and other aggregate functions
            if '*' in col and any(agg in col.lower() for agg in ['count(', 'sum(', 'avg(', 'min(', 'max(']):
                formatted_columns.append(col)
            else:
                # Handle 'column AS alias' format
                parts = col.split(' as ')
                if len(parts) == 2:
                    col_name, alias = parts
                    formatted_columns.append(
                        f"{self._format_identifier(col_name)} AS {dialect.format_identifier(alias)}")
                else:
                    formatted_columns.append(self._format_identifier(col))

        return f"SELECT {', '.join(formatted_columns)} FROM {table}"

    def _format_on_condition_part(self, condition_part: str, dialect) -> str:
        """Format a part of an ON condition with proper quoting."""
        # Remove any ON keyword if present
        if condition_part.upper().startswith('ON '):
            condition_part = condition_part[3:].strip()

        # Handle table.column format
        parts = condition_part.split('.')
        if len(parts) == 2:
            table, column = parts
            return f"{dialect.format_identifier(table)}.{dialect.format_identifier(column)}"

        return condition_part

    def _build_joins(self) -> List[str]:
        """Build JOIN clauses with dialect awareness.

        This method handles formatting of table names and columns in JOIN clauses
        according to the database dialect.

        Returns:
            List of formatted JOIN clauses
        """
        if not self.join_clauses:
            return []

        dialect = self.model_class.backend().dialect
        formatted_joins = []

        for join_clause in self.join_clauses:
            # Parse JOIN clause to identify and quote tables and columns
            join_lower = join_clause.lower()

            # Handle basic JOIN types
            join_type_index = -1
            for join_keyword in (' join ', ' inner join ', ' left join ', ' right join ', ' full join '):
                if join_keyword in join_lower:
                    join_type_index = join_lower.index(join_keyword) + len(join_keyword)
                    break

            if join_type_index > 0:
                # Get the join prefix (JOIN type)
                join_prefix = join_clause[:join_type_index]

                # Extract the table reference
                on_index = join_lower.find(' on ')
                using_index = join_lower.find(' using ')

                # Determine where the table reference ends
                if on_index > 0:
                    table_ref = join_clause[join_type_index:on_index].strip()
                    condition_part = join_clause[on_index:]
                elif using_index > 0:
                    table_ref = join_clause[join_type_index:using_index].strip()
                    condition_part = join_clause[using_index:]
                else:
                    # Just a simple JOIN without ON or USING
                    table_ref = join_clause[join_type_index:].strip()
                    condition_part = ""

                # Handle table reference with alias (e.g., "users AS u")
                alias_match = False
                formatted_table = ""
                for alias_keyword in (' as ', ' '):
                    if alias_keyword in table_ref.lower():
                        table_parts = table_ref.split(alias_keyword, 1)
                        if len(table_parts) == 2 and table_parts[1].strip():
                            table_name = table_parts[0].strip()
                            alias = table_parts[1].strip()
                            formatted_table = f"{dialect.format_identifier(table_name)}{alias_keyword}{dialect.format_identifier(alias)}"
                            alias_match = True
                            break

                if not alias_match:
                    # Simple table without alias
                    formatted_table = dialect.format_identifier(table_ref)

                # Format the JOIN condition if it exists
                formatted_condition = condition_part
                if ' on ' in condition_part.lower():
                    # Format column references in ON condition
                    # This is complex and would need a proper SQL parser for full correctness
                    # For now, we'll do basic formatting of common patterns
                    condition_parts = condition_part.split('=')
                    if len(condition_parts) == 2:
                        left_part = condition_parts[0].strip().replace(' on ', ' ON ')
                        right_part = condition_parts[1].strip()

                        # Try to format column references (table.column)
                        left_formatted = self._format_on_condition_part(left_part, dialect)
                        right_formatted = self._format_on_condition_part(right_part, dialect)

                        formatted_condition = f" ON {left_formatted} = {right_formatted}"

                formatted_joins.append(f"{join_prefix}{formatted_table}{formatted_condition}")
            else:
                # If we can't parse the JOIN clause, use it as is
                formatted_joins.append(join_clause)

        return formatted_joins

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
        """Build ORDER BY clause with proper column quoting."""
        if not self.order_clauses:
            return None

        dialect = self.model_class.backend().dialect
        formatted_clauses = []

        for clause in self.order_clauses:
            # Handle cases that contain commas, e.g. "column1, column2"
            if ',' in clause and not any(agg in clause.lower() for agg in ['(', ')']):
                # Split and format each column name separately
                columns = [col.strip() for col in clause.split(',')]
                sub_formatted = []

                for col in columns:
                    # Process the "column ASC/DESC" format
                    parts = col.split()
                    if len(parts) == 2 and parts[1].upper() in ('ASC', 'DESC'):
                        column = parts[0]
                        direction = parts[1]
                        sub_formatted.append(f"{self._format_identifier(column, dialect)} {direction}")
                    else:
                        # Simple columns or complex expressions
                        sub_formatted.append(self._format_identifier(col, dialect))

                formatted_clauses.append(", ".join(sub_formatted))
            else:
                # Process the "column ASC/DESC" format
                parts = clause.split()
                if len(parts) == 2 and parts[1].upper() in ('ASC', 'DESC'):
                    column = parts[0]
                    direction = parts[1]
                    formatted_clauses.append(f"{self._format_identifier(column, dialect)} {direction}")
                else:
                    # Simple columns or complex expressions
                    formatted_clauses.append(self._format_identifier(clause, dialect))

        return f"ORDER BY {', '.join(formatted_clauses)}"

    def _build_limit_offset(self) -> Optional[str]:
        """Build LIMIT/OFFSET clause using dialect."""
        dialect = self.model_class.backend().dialect
        return dialect.format_limit_offset(self.limit_count, self.offset_count)

    def _replace_question_marks(self, sql: str, placeholder: str) -> str:
        """Replace question mark placeholders with database-specific placeholders.

        This method carefully replaces question marks that are used as parameter
        placeholders, while preserving question marks that might appear in string literals.

        Args:
            sql: Original SQL with question mark placeholders
            placeholder: Database-specific placeholder to use

        Returns:
            SQL with replaced placeholders
        """
        # Simple implementation: directly replace all question marks
        # Note: This implementation assumes all question marks in SQL are placeholders, not part of string literals
        # For complex cases, more sophisticated parsing might be needed

        # Check if we need indexed placeholders (e.g., $1, $2, $3 for PostgreSQL)
        if placeholder.find('%d') != -1:
            # For indexed placeholders
            parts = []
            param_index = 1
            i = 0
            while i < len(sql):
                if sql[i] == '?':
                    # Replace with indexed placeholder
                    parts.append(placeholder % param_index)
                    param_index += 1
                else:
                    parts.append(sql[i])
                i += 1
            return ''.join(parts)
        else:
            # For non-indexed placeholders
            return sql.replace('?', placeholder)

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

        raw_sql = " ".join(query_parts)
        params = tuple(all_params)

        # Get the target database placeholder
        backend = self.model_class.backend()
        placeholder = backend.dialect.get_placeholder()

        # Only replace if the placeholder is not a question mark
        if placeholder != '?':
            # Replace all question marks with the correct placeholder
            # Note: We need to handle question marks that might appear in string literals
            processed_sql = self._replace_question_marks(raw_sql, placeholder)
        else:
            processed_sql = raw_sql

        return processed_sql, params

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

    def to_dict(self, include: Optional[Set[str]] = None, exclude: Optional[Set[str]] = None,
                direct_dict: bool = False) -> 'DictQuery':
        """Convert query results to dictionary format.

        This method provides two approaches to dictionary conversion:

        1. Standard mode (default): First instantiates model objects (with validation),
           then converts them to dictionaries

        2. Direct dictionary mode: Bypasses model instantiation entirely and returns
           raw dictionaries from the database. This is useful for JOIN queries or
           when the result set contains columns not defined in the model.

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
        from .dict_query import DictQuery
        return DictQuery(self, include, exclude, direct_dict)

    def __copy__(self):
        """Implement shallow copy protocol.

        This method creates a new instance of the query with base properties
        copied. Mutable collections are also copied to prevent shared references.

        Returns:
            A new instance of the query with basic properties copied.
        """
        # Create a new instance of the same class
        cls = self.__class__
        result = cls.__new__(cls)

        # Initialize with the model class
        result.__init__(self.model_class)

        # Copy basic properties
        result.condition_groups = [group.copy() for group in self.condition_groups]
        result.current_group = self.current_group
        result.order_clauses = self.order_clauses.copy()
        result.join_clauses = self.join_clauses.copy()

        # Copy select columns (if not None)
        if self.select_columns is not None:
            result.select_columns = self.select_columns.copy()
        else:
            result.select_columns = None

        # Copy limit and offset values
        result.limit_count = self.limit_count
        result.offset_count = self.offset_count

        # Copy explain settings if enabled
        if hasattr(self, '_explain_enabled'):
            result._explain_enabled = self._explain_enabled
            if hasattr(self, '_explain_options'):
                # Note: _explain_options might need deep copying,
                # but we'll handle it in __deepcopy__
                result._explain_options = self._explain_options

        return result

    def __deepcopy__(self, memo):
        """Implement deep copy protocol.

        This method creates a completely independent copy of the query,
        ensuring all nested objects are also deeply copied.

        Args:
            memo: Dictionary of already copied objects to avoid infinite recursion

        Returns:
            A completely independent copy of the query
        """
        import copy

        # Start with a shallow copy
        result = self.__copy__()

        # Track the copied object to avoid infinite recursion
        memo[id(self)] = result

        # Deep copy complex objects that might contain references
        if hasattr(self, '_explain_options'):
            result._explain_options = copy.deepcopy(self._explain_options, memo)

        # Handle eager loading configuration with deep copy
        if hasattr(self, '_eager_loads'):
            result._eager_loads = copy.deepcopy(self._eager_loads, memo)

        return result

    def clone(self) -> 'IQuery[ModelT]':
        """Create a deep copy of the current query object.

        This method provides a convenient interface to create an independent
        copy of the query for separate modifications.

        Returns:
            IQuery[ModelT]: A new independent query instance with same configuration

        Note:
            This is a wrapper around __deepcopy__ for backward compatibility
            and convenient API use.
        """
        import copy
        return copy.deepcopy(self)
