# src/rhosocial/activerecord/query/join.py
"""Enhanced join methods implementation for ActiveQuery with SQL standard compliance."""
import logging

from ..interface import ModelT, IQuery


class JoinQueryMixin(IQuery[ModelT]):
    """Enhanced join methods for ActiveQuery with SQL standard compliance.

    This mixin provides more intuitive and database-agnostic join methods,
    abstracting away SQL complexity and handling cross-database compatibility.

    Supported join types include:
    - INNER JOIN: Returns rows when there is a match in both tables
    - LEFT [OUTER] JOIN: Returns all rows from the left table and matched rows from the right
    - RIGHT [OUTER] JOIN: Returns all rows from the right table and matched rows from the left
    - FULL [OUTER] JOIN: Returns all rows when there is a match in one of the tables
    - CROSS JOIN: Returns the Cartesian product of both tables

    Additionally provides helper methods for:
    - Custom join conditions (join_on)
    - Many-to-many relationships (join_through)
    - Model-defined relationships (join_relation)
    - Natural joins (natural_join)
    """

    def inner_join(self, table: str, foreign_key: str, primary_key: str = None,
                   alias: str = None) -> 'IQuery[ModelT]':
        """Add INNER JOIN clause with simplified syntax.

        Performs an inner join that returns only matching rows from both tables.

        Args:
            table: Table to join
            foreign_key: Foreign key column, can be "column" or "table.column"
            primary_key: Primary key column, defaults to "{main_table}.id"
            alias: Optional alias for the joined table

        Returns:
            Query instance for method chaining

        Examples:
            # Join orders to users
            User.query().inner_join('orders', 'user_id')
            # SQL: INNER JOIN orders ON orders.user_id = users.id

            # With explicit column names
            User.query().inner_join('orders', 'orders.user_id', 'users.id')
            # SQL: INNER JOIN orders ON orders.user_id = users.id

            # With table alias
            User.query().inner_join('orders', 'user_id', alias='o')
            # SQL: INNER JOIN orders AS o ON o.user_id = users.id
        """
        return self._build_join("INNER JOIN", table, foreign_key, primary_key, alias)

    def left_join(self, table: str, foreign_key: str, primary_key: str = None,
                  alias: str = None, outer: bool = False) -> 'IQuery[ModelT]':
        """Add LEFT [OUTER] JOIN clause with simplified syntax.

        Performs a left join that returns all rows from the left table and matching rows
        from the right table. When no match exists, NULL values are returned for right table columns.

        Automatically selects main table columns to ensure cross-database compatibility.

        Args:
            table: Table to join
            foreign_key: Foreign key column, can be "column" or "table.column"
            primary_key: Primary key column, defaults to "{main_table}.id"
            alias: Optional alias for the joined table
            outer: Whether to include the OUTER keyword (SQL standard compliant)

        Returns:
            Query instance for method chaining

        Examples:
            # Get all users with their orders (if any)
            User.query().left_join('orders', 'user_id')
            # SQL: LEFT JOIN orders ON orders.user_id = users.id

            # With OUTER keyword (SQL standard)
            User.query().left_join('orders', 'user_id', outer=True)
            # SQL: LEFT OUTER JOIN orders ON orders.user_id = users.id

            # With table alias
            User.query().left_join('orders', 'user_id', alias='o')
            # SQL: LEFT JOIN orders AS o ON o.user_id = users.id
        """
        # Ensure primary table columns are explicitly selected for cross-database compatibility
        if not self.select_columns or self.select_columns == ["*"]:
            self.select(f"{self.model_class.table_name()}.*")

        join_type = "LEFT OUTER JOIN" if outer else "LEFT JOIN"
        return self._build_join(join_type, table, foreign_key, primary_key, alias)

    def right_join(self, table: str, foreign_key: str, primary_key: str = None,
                   alias: str = None, outer: bool = False) -> 'IQuery[ModelT]':
        """Add RIGHT [OUTER] JOIN clause with simplified syntax.

        Performs a right join that returns all rows from the right table and matching rows
        from the left table. When no match exists, NULL values are returned for left table columns.

        Note: Not all databases support RIGHT JOIN (e.g., SQLite). For maximum compatibility,
        consider using LEFT JOIN with tables reversed.

        Args:
            table: Table to join
            foreign_key: Foreign key column, can be "column" or "table.column"
            primary_key: Primary key column, defaults to "{main_table}.id"
            alias: Optional alias for the joined table
            outer: Whether to include the OUTER keyword (SQL standard compliant)

        Returns:
            Query instance for method chaining

        Examples:
            # Get all orders with their users
            User.query().right_join('orders', 'user_id')
            # SQL: RIGHT JOIN orders ON orders.user_id = users.id

            # With OUTER keyword (SQL standard)
            User.query().right_join('orders', 'user_id', outer=True)
            # SQL: RIGHT OUTER JOIN orders ON orders.user_id = users.id
        """
        join_type = "RIGHT OUTER JOIN" if outer else "RIGHT JOIN"
        return self._build_join(join_type, table, foreign_key, primary_key, alias)

    def full_join(self, table: str, foreign_key: str, primary_key: str = None,
                  alias: str = None, outer: bool = True) -> 'IQuery[ModelT]':
        """Add FULL [OUTER] JOIN clause with simplified syntax.

        Performs a full join that returns all rows from both tables.
        When no match exists, NULL values are returned for the non-matching side.

        Note: Not all databases support FULL [OUTER] JOIN (e.g., MySQL, SQLite).

        Args:
            table: Table to join
            foreign_key: Foreign key column, can be "column" or "table.column"
            primary_key: Primary key column, defaults to "{main_table}.id"
            alias: Optional alias for the joined table
            outer: Whether to include the OUTER keyword (SQL standard compliant)
                  Defaults to True as FULL JOIN is less common than FULL OUTER JOIN

        Returns:
            Query instance for method chaining

        Examples:
            # Get all users and all orders with matches where possible
            User.query().full_join('orders', 'user_id')
            # SQL: FULL OUTER JOIN orders ON orders.user_id = users.id

            # Without OUTER keyword
            User.query().full_join('orders', 'user_id', outer=False)
            # SQL: FULL JOIN orders ON orders.user_id = users.id
        """
        join_type = "FULL OUTER JOIN" if outer else "FULL JOIN"
        return self._build_join(join_type, table, foreign_key, primary_key, alias)

    def cross_join(self, table: str, alias: str = None) -> 'IQuery[ModelT]':
        """Add CROSS JOIN clause (Cartesian product).

        Performs a cross join that returns the Cartesian product of rows from both tables.
        Each row from the first table is paired with every row from the second table.

        Args:
            table: Table to join
            alias: Optional alias for the joined table

        Returns:
            Query instance for method chaining

        Examples:
            # Join all users with all products (Cartesian product)
            User.query().cross_join('products')
            # SQL: CROSS JOIN products

            # With table alias
            User.query().cross_join('products', alias='p')
            # SQL: CROSS JOIN products AS p
        """
        # Handle table reference with optional alias
        table_ref = f"{table} AS {alias}" if alias else table

        # Construct join clause
        join_clause = f"CROSS JOIN {table_ref}"

        self._log(logging.DEBUG, f"Adding cross join: {join_clause}")

        # Add to query
        return self.join(join_clause)

    def natural_join(self, table: str, join_type: str = "INNER",
                     alias: str = None, outer: bool = False) -> 'IQuery[ModelT]':
        """Add NATURAL JOIN clause.

        Performs a join based on common column names in both tables.
        The ON clause is implicitly determined by matching column names.

        Args:
            table: Table to join
            join_type: Type of join (INNER, LEFT, RIGHT, FULL)
            alias: Optional alias for the joined table
            outer: Whether to include the OUTER keyword

        Returns:
            Query instance for method chaining

        Examples:
            # Natural join on tables with matching column names
            Order.query().natural_join('users')
            # SQL: NATURAL INNER JOIN users

            # Natural left join
            Order.query().natural_join('users', join_type='LEFT', outer=True)
            # SQL: NATURAL LEFT OUTER JOIN users
        """
        # Process join type with optional OUTER keyword
        if outer and join_type in ('LEFT', 'RIGHT', 'FULL'):
            join_type = f"{join_type} OUTER"

        # Handle table reference with optional alias
        table_ref = f"{table} AS {alias}" if alias else table

        # Construct join clause
        join_clause = f"NATURAL {join_type} JOIN {table_ref}"

        # Special handling for LEFT JOIN to ensure cross-database compatibility
        if join_type.startswith("LEFT") and (not self.select_columns or self.select_columns == ["*"]):
            self.select(f"{self.model_class.table_name()}.*")

        self._log(logging.DEBUG, f"Adding natural join: {join_clause}")

        # Add to query
        return self.join(join_clause)

    def _build_join(self, join_type: str, table: str, foreign_key: str,
                    primary_key: str = None, alias: str = None) -> 'IQuery[ModelT]':
        """Build a join clause with proper handling of table and column references.

        Args:
            join_type: Type of join (INNER JOIN, LEFT JOIN, etc.)
            table: Table to join
            foreign_key: Foreign key column
            primary_key: Primary key column
            alias: Table alias

        Returns:
            Query instance for method chaining
        """
        # Get current table name
        main_table = self.model_class.table_name()

        # Handle table reference with optional alias
        table_ref = f"{table} AS {alias}" if alias else table
        table_name = alias if alias else table

        # Process foreign key column
        if '.' in foreign_key:
            # Already qualified with table
            fk_col = foreign_key
        else:
            # Default assume it's a column in the joined table
            fk_col = f"{table_name}.{foreign_key}"

        # Process primary key column
        if primary_key is None:
            # Default to main table's id
            pk_col = f"{main_table}.id"
        else:
            pk_col = primary_key

        # Build join clause
        join_clause = f"{join_type} {table_ref} ON {fk_col} = {pk_col}"

        self._log(logging.DEBUG, f"Built join clause: {join_clause}")

        # Add to query
        return self.join(join_clause)

    def join_on(self, table: str, condition: str, join_type: str = "INNER JOIN",
                alias: str = None, params: tuple = None, outer: bool = False) -> 'IQuery[ModelT]':
        """Add join with custom ON condition.

        This method allows for more complex join conditions beyond simple key matching.

        Args:
            table: Table to join
            condition: Custom join condition (ON clause)
            join_type: Type of join (INNER, LEFT, RIGHT, FULL)
            alias: Optional table alias
            params: Query parameters for condition placeholders
            outer: Whether to include the OUTER keyword for outer joins

        Returns:
            Query instance for method chaining

        Examples:
            # Join with complex condition
            Order.query().join_on(
                'users',
                'users.id = orders.user_id AND users.status = ?',
                join_type='LEFT',
                params=('active',)
            )
            # SQL: LEFT JOIN users ON users.id = orders.user_id AND users.status = 'active'

            # Using OUTER keyword
            Order.query().join_on(
                'users',
                'users.id = orders.user_id',
                join_type='FULL',
                outer=True
            )
            # SQL: FULL OUTER JOIN users ON users.id = orders.user_id

            # Join with table alias
            Order.query().join_on(
                'users',
                'u.id = orders.user_id',
                alias='u'
            )
            # SQL: INNER JOIN users AS u ON u.id = orders.user_id
        """
        # Process join type with optional OUTER keyword
        if outer and join_type in ('LEFT', 'RIGHT', 'FULL'):
            join_type = f"{join_type} OUTER"

        # Ensure JOIN is included
        if not "JOIN" in join_type:
            join_type = f"{join_type} JOIN"

        # Handle table reference with optional alias
        table_ref = f"{table} AS {alias}" if alias else table

        # Construct join clause
        join_clause = f"{join_type} {table_ref} ON {condition}"

        # Handle params if provided
        if params:
            for param in params:
                self.condition_groups[self.current_group].append(("", (param,), 'AND'))

        # Special handling for LEFT JOIN to ensure cross-database compatibility
        if join_type.startswith("LEFT") and (not self.select_columns or self.select_columns == ["*"]):
            self.select(f"{self.model_class.table_name()}.*")

        self._log(logging.DEBUG, f"Adding custom join: {join_clause}")

        # Add to query
        return self.join(join_clause)

    def join_through(self, intermediate_table: str, target_table: str,
                     fk1: str, fk2: str, join_type: str = "INNER JOIN",
                     outer: bool = False) -> 'IQuery[ModelT]':
        """Join through an intermediate table (for many-to-many relationships).

        Args:
            intermediate_table: Junction/pivot table
            target_table: Target table to join
            fk1: First join condition (main table to intermediate)
            fk2: Second join condition (intermediate to target)
            join_type: Type of join (INNER JOIN, LEFT JOIN, etc.)
            outer: Whether to include the OUTER keyword for outer joins

        Returns:
            Query instance for method chaining

        Examples:
            # Join users to roles through user_roles
            User.query().join_through(
                'user_roles',    # Intermediate table
                'roles',         # Target table
                'users.id = user_roles.user_id',  # First join
                'user_roles.role_id = roles.id'   # Second join
            )
            # SQL:
            # INNER JOIN user_roles ON users.id = user_roles.user_id
            # INNER JOIN roles ON user_roles.role_id = roles.id

            # With LEFT JOIN
            User.query().join_through(
                'user_roles',
                'roles',
                'users.id = user_roles.user_id',
                'user_roles.role_id = roles.id',
                join_type='LEFT JOIN'
            )
        """
        # Process join type with optional OUTER keyword
        if outer and any(t in join_type for t in ('LEFT', 'RIGHT', 'FULL')):
            # Check if "OUTER" is already included
            if "OUTER" not in join_type:
                join_parts = join_type.split()
                if len(join_parts) >= 2 and join_parts[0] in ('LEFT', 'RIGHT', 'FULL'):
                    join_type = f"{join_parts[0]} OUTER {join_parts[1]}"

        # First join to intermediate table
        self.join(f"{join_type} {intermediate_table} ON {fk1}")

        # Then join to target table
        return self.join(f"{join_type} {target_table} ON {fk2}")
