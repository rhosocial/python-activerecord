# Extending Existing Backends

This guide explains how to extend or modify the behavior of existing database backends in rhosocial ActiveRecord.

## Introduction

Sometimes you may need to customize the behavior of an existing database backend without creating an entirely new implementation. rhosocial ActiveRecord provides several approaches for extending existing backends to add functionality or modify behavior.

## When to Extend an Existing Backend

Extending an existing backend is appropriate when:

1. You need to add support for database-specific features not included in the standard implementation
2. You want to modify the behavior of certain operations for your specific use case
3. You need to integrate with additional libraries or services while maintaining compatibility with the base backend
4. You want to add monitoring, logging, or performance tracking to database operations

## Extension Methods

There are several approaches to extending existing backends:

### 1. Subclassing

The most straightforward approach is to subclass an existing backend implementation:

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

class ExtendedSQLiteBackend(SQLiteBackend):
    """Extended SQLite backend with custom functionality"""
    
    def execute(self, query, params=None, **options):
        """Override execute method to add custom behavior"""
        # Add pre-execution logic here
        self.logger.debug(f"Custom logging: Executing query: {query}")
        
        # Call the parent implementation
        result = super().execute(query, params, **options)
        
        # Add post-execution logic here
        self.logger.debug(f"Query returned {len(result.rows)} rows")
        
        return result
    
    def connect(self):
        """Override connect method to add custom initialization"""
        # Call the parent implementation
        super().connect()
        
        # Add custom initialization
        cursor = self._get_cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # Example: Force WAL mode
```

### 2. Extending the Dialect

You can extend the SQL dialect to customize SQL generation:

```python
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect, MySQLBuilder

class ExtendedMySQLDialect(MySQLDialect):
    """Extended MySQL dialect with custom SQL generation"""
    
    def create_builder(self):
        """Create a custom SQL builder"""
        return ExtendedMySQLBuilder(self)

class ExtendedMySQLBuilder(MySQLBuilder):
    """Extended MySQL SQL builder"""
    
    def build_select(self, query_parts):
        """Override select query building to add custom behavior"""
        # Add custom hints or options to SELECT queries
        if 'hints' in query_parts and query_parts['hints']:
            query_parts['select'] = f"SELECT /*+ {query_parts['hints']} */"
        
        # Call the parent implementation
        return super().build_select(query_parts)
```

### 3. Custom Type Handling

Extend the type mapper to add support for custom types:

```python
from rhosocial.activerecord.backend.impl.pgsql.types import PostgreSQLTypeMapper
from rhosocial.activerecord.backend.dialect import TypeMapping, DatabaseType

class ExtendedPostgreSQLTypeMapper(PostgreSQLTypeMapper):
    """Extended PostgreSQL type mapper with custom types"""
    
    def __init__(self):
        super().__init__()
        
        # Add or override type mappings
        self._type_map[DatabaseType.CUSTOM] = TypeMapping("JSONB")  # Map CUSTOM to JSONB
        
        # Add a custom type handler
        self._value_handlers[DatabaseType.CUSTOM] = self._handle_custom_type
    
    def _handle_custom_type(self, value):
        """Custom type conversion handler"""
        import json
        if isinstance(value, dict) or isinstance(value, list):
            return json.dumps(value)
        return str(value)
```

## Integration with ActiveRecord

To use your extended backend, you need to register it with ActiveRecord:

```python
from rhosocial.activerecord import configure
from your_module import ExtendedSQLiteBackend

# Create an instance of your extended backend
extended_backend = ExtendedSQLiteBackend(database='your_database.db')

# Configure ActiveRecord to use your extended backend
configure(backend=extended_backend)
```

Alternatively, you can modify the backend factory to support your extended backend:

```python
from rhosocial.activerecord.backend import create_backend as original_create_backend
from your_module import ExtendedSQLiteBackend, ExtendedMySQLBackend

def create_backend(backend_type, **config):
    """Extended backend factory"""
    if backend_type == 'extended_sqlite':
        return ExtendedSQLiteBackend(**config)
    elif backend_type == 'extended_mysql':
        return ExtendedMySQLBackend(**config)
    else:
        return original_create_backend(backend_type, **config)

# Replace the original factory
import rhosocial.activerecord.backend
rhosocial.activerecord.backend.create_backend = create_backend
```

## Practical Examples

### Adding Query Profiling

```python
import time
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

class ProfilingMySQLBackend(MySQLBackend):
    """MySQL backend with query profiling"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.query_stats = []
    
    def execute(self, query, params=None, **options):
        """Execute a query with profiling"""
        start_time = time.time()
        
        try:
            result = super().execute(query, params, **options)
            duration = time.time() - start_time
            
            # Record query statistics
            self.query_stats.append({
                'query': query,
                'params': params,
                'duration': duration,
                'rows': len(result.rows) if result.rows else 0,
                'success': True
            })
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            
            # Record failed query
            self.query_stats.append({
                'query': query,
                'params': params,
                'duration': duration,
                'error': str(e),
                'success': False
            })
            
            raise
    
    def get_slow_queries(self, threshold=1.0):
        """Get queries that took longer than the threshold"""
        return [q for q in self.query_stats if q['duration'] > threshold]
```

### Adding Custom JSON Operations

```python
from rhosocial.activerecord.backend.impl.pgsql import PostgreSQLBackend
from rhosocial.activerecord.backend.impl.pgsql.dialect import PostgreSQLDialect

class JSONEnhancedPostgreSQLDialect(PostgreSQLDialect):
    """PostgreSQL dialect with enhanced JSON operations"""
    
    def json_contains(self, column, value):
        """Check if JSON column contains a value"""
        return f"{column} @> %s::jsonb"
    
    def json_extract_path(self, column, path):
        """Extract a value from a JSON path"""
        return f"{column}#>>%s"

class JSONEnhancedPostgreSQLBackend(PostgreSQLBackend):
    """PostgreSQL backend with enhanced JSON support"""
    
    @property
    def dialect(self):
        """Get SQL dialect for this backend"""
        if not hasattr(self, '_dialect_instance'):
            self._dialect_instance = JSONEnhancedPostgreSQLDialect()
        return self._dialect_instance
```

## Best Practices

1. **Minimize Overrides**: Only override the methods you need to change
2. **Call Parent Methods**: Always call the parent implementation unless you're completely replacing the functionality
3. **Maintain Compatibility**: Ensure your extensions maintain compatibility with the ActiveRecord API
4. **Test Thoroughly**: Create comprehensive tests for your extended backend
5. **Document Changes**: Clearly document the changes and additions in your extended backend

## Limitations and Considerations

1. **Upgrade Compatibility**: Your extensions may break when upgrading to newer versions of rhosocial ActiveRecord
2. **Performance Impact**: Complex extensions may impact performance
3. **Maintenance Burden**: You'll need to maintain your extensions as the base implementation evolves

## Implementation Location

When implementing your extended backend, you have flexibility in where to place your code:

1. **Within the ActiveRecord Package**: You can place your implementation directly in the `rhosocial.activerecord.backend.impl` directory if you're modifying the core package.
2. **In a Separate Package**: You can create your own package structure outside the core ActiveRecord package, which is recommended if you plan to distribute your extension separately.

Both approaches are valid, with the separate package offering better isolation and easier distribution.

## Testing Your Extended Backend

Thoroughly testing your extended backend is crucial for ensuring reliability. You should:

1. **Mirror Existing Tests**: Study and mirror the test structure of existing backends (e.g., in the `tests/rhosocial/activerecord/backend` directory)
2. **Ensure Branch Coverage**: Write tests that cover all code branches and edge cases
3. **Simulate Real-World Scenarios**: Create tests that simulate various usage scenarios your backend will encounter
4. **Test Integration**: Verify that your extended backend works correctly with the rest of the ActiveRecord framework

## Conclusion

Extending existing database backends provides a powerful way to customize rhosocial ActiveRecord for your specific needs without creating an entirely new implementation. By following the approaches outlined in this guide, you can add functionality, modify behavior, or integrate with additional services while maintaining compatibility with the ActiveRecord framework.