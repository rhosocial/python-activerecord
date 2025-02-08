# SQLite Implementation

This document covers the implementation details of the SQLite backend in RhoSocial ActiveRecord.

## Backend Implementation

### Core Backend Class

```python
class SQLiteBackend(StorageBackend):
    """SQLite backend implementation."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cursor = None
        self._type_mapper = SQLiteTypeMapper()
        self._value_mapper = SQLiteValueMapper(self.config)
        self._transaction_manager = None
        self._dialect = SQLiteDialect()

    def connect(self) -> None:
        """Establish database connection."""
        try:
            self._connection = sqlite3.connect(
                self.config.database,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                isolation_level=None  # Manual transaction management
            )
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.row_factory = sqlite3.Row
            self._connection.text_factory = str
        except sqlite3.Error as e:
            raise ConnectionError(f"Failed to connect: {str(e)}")

    def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None,
        returning: bool = False,
        column_types: Optional[Dict[str, DatabaseType]] = None
    ) -> QueryResult:
        """Execute SQL statement."""
        start_time = time.perf_counter()
        try:
            if not self._connection:
                self.connect()

            cursor = self._cursor or self._connection.cursor()

            # Process SQL and parameters using dialect
            final_sql, final_params = self.build_sql(sql, params)

            # Convert parameters
            if final_params:
                processed_params = tuple(
                    self._value_mapper.to_database(value, None)
                    for value in final_params
                )
                cursor.execute(final_sql, processed_params)
            else:
                cursor.execute(final_sql)

            if returning:
                # Get raw data
                rows = cursor.fetchall()

                # Convert types if mapping provided
                if column_types:
                    data = []
                    for row in rows:
                        converted_row = {}
                        for key, value in dict(row).items():
                            db_type = column_types.get(key)
                            converted_row[key] = (
                                self._value_mapper.from_database(value, db_type)
                                if db_type is not None
                                else value
                            )
                        data.append(converted_row)
                else:
                    data = [dict(row) for row in rows]
            else:
                data = None

            return QueryResult(
                data=data,
                affected_rows=cursor.rowcount,
                last_insert_id=cursor.lastrowid,
                duration=time.perf_counter() - start_time
            )
        except Exception as e:
            self._handle_error(e)
```

## Type System

### Type Mapping

```python
class SQLiteTypeMapper(TypeMapper):
    """SQLite type mapping implementation."""
    
    def get_column_type(self, db_type: DatabaseType, **params) -> str:
        """Get SQLite column type definition."""
        mapping = SQLITE_TYPE_MAPPINGS.get(db_type)
        if not mapping:
            raise ValueError(f"Unsupported type: {db_type}")

        sql_type = mapping.db_type
        if mapping.format_func:
            sql_type = mapping.format_func(sql_type, params)

        constraints = {k: v for k, v in params.items()
                     if k in ['primary_key', 'autoincrement', 'unique',
                             'not_null', 'default']}

        return SQLiteColumnType(sql_type, **constraints)

    def get_placeholder(self, db_type: DatabaseType) -> str:
        """Get parameter placeholder."""
        return "?"
```

### Value Conversion

```python
class SQLiteValueMapper(ValueMapper):
    """SQLite value mapper implementation."""

    def __init__(self, config: ConnectionConfig):
        self.config = config
        # Define basic type converters
        self._base_converters = {
            int: int,
            float: float,
            Decimal: str,
            bool: lambda x: 1 if x else 0,
            uuid.UUID: str,
            date: convert_datetime,
            time: convert_datetime,
            datetime: convert_datetime,
            dict: safe_json_dumps,
            list: array_converter,
            tuple: array_converter,
        }
        # Define database type converters
        self._db_type_converters = {
            DatabaseType.BOOLEAN: lambda v: 1 if v else 0,
            DatabaseType.DATE: lambda v: convert_datetime(v, timezone=self.config.timezone),
            DatabaseType.TIME: lambda v: convert_datetime(v, timezone=self.config.timezone),
            DatabaseType.DATETIME: lambda v: convert_datetime(v, timezone=self.config.timezone),
            DatabaseType.TIMESTAMP: lambda v: convert_datetime(v, timezone=self.config.timezone),
            DatabaseType.JSON: safe_json_dumps,
            DatabaseType.ARRAY: array_converter,
            DatabaseType.UUID: str,
            DatabaseType.DECIMAL: str,
        }
```

## SQL Dialect

### Dialect Implementation

```python
class SQLiteDialect(SQLDialectBase):
    """SQLite dialect implementation."""

    def format_expression(self, expr: SQLExpressionBase) -> str:
        """Format SQLite expression."""
        if not isinstance(expr, SQLiteExpression):
            raise ValueError(f"Unsupported expression type: {type(expr)}")
        return expr.format(self)

    def get_placeholder(self) -> str:
        """Get SQLite parameter placeholder."""
        return "?"

    def create_expression(self, expression: str) -> SQLiteExpression:
        """Create SQLite expression."""
        return SQLiteExpression(expression)
```

### Expression Handling

```python
class SQLiteExpression(SQLExpressionBase):
    """SQLite expression implementation."""

    def format(self, dialect: SQLDialectBase) -> str:
        """Format SQLite expression."""
        return self.expression

class SQLBuilder:
    """SQL Builder for SQLite."""

    def __init__(self, dialect: SQLDialectBase):
        self.dialect = dialect

    def build(self, sql: str, params: Optional[Tuple] = None) -> Tuple[str, Tuple]:
        """Build SQL and parameters."""
        if not params:
            return sql, ()

        # Find all placeholder positions
        placeholder = self.dialect.get_placeholder()
        placeholder_positions = []
        pos = 0
        while True:
            pos = sql.find(placeholder, pos)
            if pos == -1:
                break
            placeholder_positions.append(pos)
            pos += len(placeholder)

        if len(placeholder_positions) != len(params):
            raise ValueError(
                f"Parameter count mismatch: expected {len(placeholder_positions)}, "
                f"got {len(params)}"
            )

        # Process parameters and expressions
        result = list(sql)
        final_params = []
        param_positions = []

        # Find parameter positions
        for i, param in enumerate(params):
            if not isinstance(param, SQLExpressionBase):
                param_positions.append(i)
                final_params.append(param)

        # Replace expressions
        for i in range(len(params) - 1, -1, -1):
            if isinstance(params[i], SQLExpressionBase):
                pos = placeholder_positions[i]
                expr_str = self.dialect.format_expression(params[i])
                result[pos:pos + len(placeholder)] = expr_str

        return ''.join(result), tuple(final_params)
```

## Transaction Management

### Transaction Manager

```python
class SQLiteTransactionManager(TransactionManager):
    """SQLite transaction manager implementation."""

    _ISOLATION_LEVELS = {
        IsolationLevel.SERIALIZABLE: "IMMEDIATE",  # SQLite defaults to SERIALIZABLE
        IsolationLevel.READ_UNCOMMITTED: "DEFERRED",
    }

    def __init__(self, connection):
        super().__init__()
        self._connection = connection
        self._connection.isolation_level = None

    def _get_isolation_pragma(self) -> Optional[str]:
        """Get PRAGMA setting for isolation level."""
        if self._isolation_level == IsolationLevel.READ_UNCOMMITTED:
            return "PRAGMA read_uncommitted = 1"
        return "PRAGMA read_uncommitted = 0"

    def _do_begin(self) -> None:
        """Begin SQLite transaction."""
        try:
            if self._isolation_level:
                level = self._ISOLATION_LEVELS.get(self._isolation_level)
                if level:
                    self._connection.execute(f"BEGIN {level} TRANSACTION")
                    pragma = self._get_isolation_pragma()
                    if pragma:
                        self._connection.execute(pragma)
                else:
                    raise TransactionError(
                        f"Unsupported isolation level: {self._isolation_level}"
                    )
            else:
                self._connection.execute("BEGIN IMMEDIATE TRANSACTION")
        except Exception as e:
            raise TransactionError(f"Failed to begin transaction: {str(e)}")

    def _do_commit(self) -> None:
        """Commit SQLite transaction."""
        try:
            self._connection.execute("COMMIT")
        except Exception as e:
            raise TransactionError(f"Failed to commit transaction: {str(e)}")

    def _do_rollback(self) -> None:
        """Rollback SQLite transaction."""
        try:
            self._connection.execute("ROLLBACK")
        except Exception as e:
            raise TransactionError(f"Failed to rollback transaction: {str(e)}")
```

## Best Practices

1. **Type Handling**
   - Implement comprehensive type conversion
   - Handle NULL values properly
   - Support SQLite-specific types

2. **Transaction Management**
   - Use proper isolation levels
   - Implement savepoint support
   - Handle nested transactions

3. **Error Handling**
   - Convert SQLite errors to ActiveRecord errors
   - Provide detailed error messages
   - Handle connection issues

4. **Query Building**
   - Use parameterized queries
   - Handle expressions properly
   - Support complex queries

## Next Steps

1. Learn about [Custom Backends](custom_backend.md)
2. Study [Performance Optimization](../5.performance/index.md)
3. Review [Error Handling](../2.features/error_handling.md)