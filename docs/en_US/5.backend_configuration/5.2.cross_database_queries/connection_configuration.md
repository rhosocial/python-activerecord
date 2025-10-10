# Cross-database Connection Configuration

> **❌ NOT IMPLEMENTED**: The multiple database connection functionality (including master-slave configuration) described in this document is **not implemented**. This documentation describes planned functionality and is provided for future reference only. Current users should work with single database connections only. This feature may be developed in future releases with no guaranteed timeline. The API described in this document is subject to significant changes when implementation begins.

This document provides detailed information about configuring and managing connections to multiple databases in rhosocial ActiveRecord, including how to set up connections to different database systems, manage connection pools, and switch between connections at runtime.

## Basic Connection Configuration

rhosocial ActiveRecord allows you to configure and connect to multiple databases simultaneously, even if they are of different types. This capability is essential for applications that need to access data from various sources or that use different databases for different parts of the application.

### Configuring Multiple Database Connections

To work with multiple databases, you need to configure each connection separately and give each a unique name:

```python
from rhosocial.activerecord import ConnectionManager

# Configure primary database (SQLite)
primary_config = {
    'driver': 'sqlite',
    'database': 'main.db'
}

# Configure secondary database (PostgreSQL)
secondary_config = {
    'driver': 'postgresql',
    'host': 'localhost',
    'port': 5432,
    'database': 'analytics',
    'username': 'user',
    'password': 'password'
}

# Register connections with unique names
ConnectionManager.configure('primary', primary_config)
ConnectionManager.configure('secondary', secondary_config)
```

### Connection Configuration Options

Each database connection can be configured with various options depending on the database type. Here are some common configuration options:

#### Common Options for All Database Types

- `driver`: The database driver to use (e.g., 'sqlite', 'mysql', 'postgresql')
- `database`: The name of the database
- `pool_size`: Maximum number of connections to keep in the connection pool
- `pool_timeout`: Maximum time (in seconds) to wait for a connection from the pool
- `pool_recycle`: Number of seconds after which a connection is recycled
- `echo`: Whether to log SQL statements (boolean, default is False)

#### MySQL/MariaDB Specific Options

- `host`: Database server hostname or IP address
- `port`: Database server port (default is 3306)
- `username`: Username for authentication
- `password`: Password for authentication
- `charset`: Character set to use (default is 'utf8mb4')
- `ssl`: SSL configuration options (dictionary)

#### PostgreSQL Specific Options

- `host`: Database server hostname or IP address
- `port`: Database server port (default is 5432)
- `username`: Username for authentication
- `password`: Password for authentication
- `schema`: Schema to use (default is 'public')
- `sslmode`: SSL mode to use (e.g., 'require', 'verify-full')

#### Oracle Specific Options

- `host`: Database server hostname or IP address
- `port`: Database server port (default is 1521)
- `username`: Username for authentication
- `password`: Password for authentication
- `service_name`: Oracle service name
- `sid`: Oracle SID (alternative to service_name)

#### SQL Server Specific Options

- `host`: Database server hostname or IP address
- `port`: Database server port (default is 1433)
- `username`: Username for authentication
- `password`: Password for authentication
- `driver`: ODBC driver to use (e.g., 'ODBC Driver 17 for SQL Server')
- `trusted_connection`: Whether to use Windows authentication (boolean)

### Connection Pooling

rhosocial ActiveRecord uses connection pooling to efficiently manage database connections. Connection pooling maintains a set of open connections that can be reused, reducing the overhead of establishing new connections for each database operation.

You can configure connection pooling parameters for each database connection:

```python
from rhosocial.activerecord import ConnectionManager

# Configure connection with pool settings
config = {
    'driver': 'postgresql',
    'host': 'localhost',
    'port': 5432,
    'database': 'myapp',
    'username': 'user',
    'password': 'password',
    'pool_size': 10,        # Maximum number of connections in the pool
    'pool_timeout': 30,     # Maximum time (in seconds) to wait for a connection
    'pool_recycle': 1800    # Recycle connections after 30 minutes
}

ConnectionManager.configure('main', config)
```

#### Pool Size Considerations

When determining the appropriate pool size for your application, consider the following factors:

- The number of concurrent requests your application handles
- The database server's maximum connection limit
- The resource usage of each connection

A general guideline is to set the pool size to match the maximum number of concurrent database operations your application needs to perform, plus a small buffer for overhead.

## Using Multiple Database Connections

### Specifying the Database Connection in Models

Once you have configured multiple connections, you can specify which connection each model should use:

```python
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    __connection__ = 'primary'  # Use the primary database
    # Model definition...

class AnalyticsData(ActiveRecord):
    __connection__ = 'secondary'  # Use the secondary database
    # Model definition...
```

### Switching Connections at Runtime

You can also switch database connections at runtime for specific operations:

```python
# Using the connection context manager
with User.using_connection('secondary'):
    # All User operations in this block will use the secondary connection
    users = User.all()

# Or using the connection method for a single query
users = User.using('secondary').all()
```

### Accessing Connection Objects Directly

In some cases, you may need to access the underlying connection object directly:

```python
from rhosocial.activerecord import get_connection

# Get a connection by name
conn = get_connection('primary')

# Use the connection for raw SQL execution
result = conn.execute_raw("SELECT COUNT(*) FROM users WHERE status = 'active'")
```

## Connection Management Strategies

### Application-level Connection Configuration

For most applications, it's best to configure all database connections at application startup:

```python
def configure_database_connections():
    # Load configuration from environment or config files
    primary_config = load_config('primary_db')
    analytics_config = load_config('analytics_db')
    reporting_config = load_config('reporting_db')
    
    # Configure connections
    ConnectionManager.configure('primary', primary_config)
    ConnectionManager.configure('analytics', analytics_config)
    ConnectionManager.configure('reporting', reporting_config)

# Call this function during application initialization
configure_database_connections()
```

### Dynamic Connection Configuration

In some cases, you may need to configure connections dynamically at runtime:

```python
def connect_to_tenant_database(tenant_id):
    # Load tenant-specific configuration
    tenant_config = get_tenant_db_config(tenant_id)
    
    # Configure connection with tenant-specific name
    connection_name = f"tenant_{tenant_id}"
    ConnectionManager.configure(connection_name, tenant_config)
    
    return connection_name

# Usage
tenant_connection = connect_to_tenant_database('tenant123')
with User.using_connection(tenant_connection):
    tenant_users = User.all()
```

### Connection Lifecycle Management

rhosocial ActiveRecord automatically manages the lifecycle of database connections, but you can explicitly control connection creation and disposal if needed:

```python
from rhosocial.activerecord import ConnectionManager

# Explicitly create all configured connections
ConnectionManager.initialize_all()

# Dispose of a specific connection
ConnectionManager.dispose('secondary')

# Dispose of all connections (e.g., during application shutdown)
ConnectionManager.dispose_all()
```

## Best Practices for Cross-database Connection Configuration

1. **Use Descriptive Connection Names**: Choose connection names that clearly indicate the purpose or content of each database.

2. **Centralize Connection Configuration**: Keep all database connection configurations in a single location for easier management.

3. **Use Environment Variables for Sensitive Information**: Store sensitive connection information (like passwords) in environment variables rather than hardcoding them.

```python
import os

config = {
    'driver': 'postgresql',
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 5432)),
    'database': os.environ.get('DB_NAME', 'myapp'),
    'username': os.environ.get('DB_USER', 'user'),
    'password': os.environ.get('DB_PASSWORD', ''),
}
```

4. **Configure Appropriate Pool Sizes**: Set connection pool sizes based on your application's needs and the capabilities of your database servers.

5. **Monitor Connection Usage**: Implement monitoring to track connection usage and detect connection leaks or pool exhaustion.

6. **Implement Connection Retry Logic**: For critical operations, implement retry logic to handle temporary connection failures.

```python
from rhosocial.activerecord import ConnectionError

def perform_critical_operation():
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            with Transaction(get_connection('primary')):
                # Perform critical database operations
                return result
        except ConnectionError as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise
            time.sleep(1)  # Wait before retrying
```

7. **Close Connections During Idle Periods**: For long-running applications with periods of inactivity, consider disposing of unused connections during idle periods.

8. **Use Read-Write Splitting When Appropriate**: For high-traffic applications, consider configuring separate connections for read and write operations.

```python
# Configure separate read and write connections
ConnectionManager.configure('primary_write', write_config)
ConnectionManager.configure('primary_read', read_config)

class User(ActiveRecord):
    __connection__ = 'primary_write'  # Default connection for writes
    
    @classmethod
    def find_active(cls):
        # Use read connection for this query
        with cls.using_connection('primary_read'):
            return cls.where(status='active').all()
```

## Troubleshooting Connection Issues

### Common Connection Problems

1. **Connection Pool Exhaustion**: If your application is experiencing slow performance or timeouts, you may be exhausting your connection pool.

   Solution: Increase the pool size or optimize your code to release connections more quickly.

2. **Connection Timeouts**: If connections are timing out, the database server may be overloaded or network issues may be present.

   Solution: Check database server load, network connectivity, and increase connection timeouts if appropriate.

3. **Authentication Failures**: Incorrect credentials or permission issues can cause authentication failures.

   Solution: Verify username, password, and ensure the user has appropriate permissions.

### Debugging Connection Issues

To debug connection issues, you can enable SQL logging:

```python
config = {
    # Other configuration options...
    'echo': True  # Enable SQL logging
}

ConnectionManager.configure('debug_connection', config)
```

You can also implement custom connection event listeners:

```python
from rhosocial.activerecord import ConnectionEvents

# Register connection event listeners
ConnectionEvents.on_checkout(lambda conn: print(f"Connection {conn.id} checked out"))
ConnectionEvents.on_checkin(lambda conn: print(f"Connection {conn.id} checked in"))
ConnectionEvents.on_connect(lambda conn: print(f"New connection {conn.id} established"))
ConnectionEvents.on_disconnect(lambda conn: print(f"Connection {conn.id} closed"))
```

## Conclusion

Properly configuring and managing database connections is essential for applications that work with multiple databases. rhosocial ActiveRecord provides a flexible and powerful connection management system that allows you to work with multiple databases of different types simultaneously, while abstracting away many of the complexities involved.

By following the best practices outlined in this document, you can ensure that your application's database connections are efficient, reliable, and secure.