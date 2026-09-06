# Connection Errors

## Overview

Connection errors are the most common issues when working with databases. This document covers error diagnosis and automatic recovery strategies.

## Connection Refused

**Symptom**: `ConnectionRefusedError` or similar when connecting.

**Common causes**:
- {database} server not running
- Wrong host or port
- Firewall blocking the connection

**Solution**:
```bash
# Verify {database} is running
{check-command}

# Test connectivity
telnet localhost {port}
```

## Authentication Failed

**Symptom**: `OperationalError` with authentication message.

**Common causes**:
- Wrong username or password
- User does not have permission to access the database
- Authentication method mismatch

**Solution**:
```bash
# Test credentials manually
{connect-command}
```

## Connection Timeout

**Symptom**: Timeout after N seconds.

**Common causes**:
- Server overloaded
- Network latency too high
- `connect_timeout` too low

**Solution**: Increase timeout or check server health:
```python
config = {Backend}ConnectionConfig(
    host='localhost',
    port={port},
    database='myapp',
    username='app',
    password='secret',
    connect_timeout=30,  # Increase timeout
)
```

## SSL Connection Error

**Symptom**: SSL-related errors during connection.

**Common causes**:
- Self-signed certificate
- SSL not configured on server
- Wrong SSL parameters

**Solution**: See [SSL/TLS Configuration](../installation_and_configuration/ssl.md).

## Connection Loss and Automatic Recovery

### Common Scenarios

- Network interruption
- {database} server restart
- Idle connection timeout
- Server-side connection kill

### Automatic Recovery Mechanism

rhosocial-activerecord provides a dual-layer recovery mechanism:

**Plan A: Pre-Query Check**

Before executing a query, check if the connection is still alive:

```python
backend = {Backend}Backend(config)
backend.connect()

# Check connection before query
if not backend.is_connected():
    backend.connect()

# Execute query
result = User.query().all()
```

**Plan B: Error Retry**

Catch connection errors and retry with reconnection:

```python
import time

def execute_with_retry(func, max_retry=3):
    for attempt in range(max_retry):
        try:
            return func()
        except Exception as e:
            if _is_connection_error(e) and attempt < max_retry - 1:
                time.sleep(0.1 * (attempt + 1))
                backend.connect()
                continue
            raise
```

### Manual Keep-Alive

For long-running applications, periodically ping the database:

```python
import time

def keep_alive(backend, interval=300):
    """Ping the database every N seconds."""
    while True:
        time.sleep(interval)
        if not backend.is_connected():
            backend.connect()
```

## Best Practices

1. **Configure timeout**: Set appropriate `connect_timeout` and `read_timeout`
2. **Monitor connections**: Track connection state and log disconnections
3. **Use connection pooling**: For high-concurrency scenarios, use connection pools
4. **Multi-process workers**: Each process should have its own connection

## Error Codes Reference

<!-- Document backend-specific error codes. Examples:

### MySQL Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 2003 | Can't connect to server | Check host, port, firewall |
| 1045 | Access denied | Check username, password |
| 2003 | Connection timeout | Increase timeout, check server |
| 2026 | SSL connection error | Check SSL configuration |
| 2013 | Lost connection | Check server, network |

### PostgreSQL SQLSTATE Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 08001 | SQLCLIENT unable to establish SQLCONNECTION | Check host, port, firewall |
| 08006 | CONNECTION FAILURE | Check server, network |
| 08001 | sqlclient unable to establish sqlconnection | Check credentials |
| 57P01 | ADMIN SHUTDOWN | Restart server |

-->

## See Also

- [SSL/TLS Configuration](../installation_and_configuration/ssl.md) — secure connections
- [Connection Management](../installation_and_configuration/pool.md) — connection lifecycle
