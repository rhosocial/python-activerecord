# Logging Configuration

Logging in rhosocial ActiveRecord is currently basic and relies on Python's standard logging module. The framework does not yet provide advanced logging capabilities.

## Setting Up Basic Logging

To enable logging in your ActiveRecord application:

```python
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# For more detailed logging (including SQL queries if available)
logging.getLogger('rhosocial.activerecord').setLevel(logging.DEBUG)
```

## Current Logging Capabilities

The current implementation provides:

- Basic SQL query logging (if implemented in the backend)
- Connection status logging
- Error logging

## Example Usage

```python
import logging
from rhosocial.activerecord import ActiveRecord

logger = logging.getLogger('rhosocial.activerecord')

# Enable debug logging to see queries
logger.setLevel(logging.DEBUG)

# Any database operations will now be logged at DEBUG level
user = User(name="Log Test", email="log@example.com")
user.save()
```

## Limitations

- No structured logging
- No automatic performance metrics
- No query execution time logging
- Limited insight into framework operations

Advanced logging and analysis features will be added in future releases.

## Setting Up Logging

rhosocial ActiveRecord provides a flexible logging system that integrates with Python's standard logging module.

### Basic Logging Configuration

```python
import logging
from rhosocial.activerecord import configure_logging

# Configure global logging
configure_logging(
    level=logging.INFO,  # Global log level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    file_path="activerecord.log"  # Optional: log to file
)
```

### Component-Specific Logging

You can configure different log levels for specific components:

```python
# Configure logging for specific components
configure_logging(component="query", level=logging.DEBUG)
configure_logging(component="transaction", level=logging.INFO)
configure_logging(component="relation", level=logging.WARNING)
```

### Available Logging Components

rhosocial ActiveRecord provides several logging components:

- `query`: Logs SQL queries and their parameters
- `transaction`: Logs transaction operations (begin, commit, rollback)
- `relation`: Logs relationship loading and caching
- `model`: Logs model operations (create, update, delete)
- `migration`: Logs schema migration operations
- `connection`: Logs database connection events
- `cache`: Logs caching operations

### Logging in Production

For production environments, consider these logging practices:

```python
# Production logging configuration
configure_logging(
    level=logging.WARNING,  # Only log warnings and errors
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    file_path="/var/log/myapp/activerecord.log",
    max_bytes=10485760,  # 10MB
    backup_count=5  # Keep 5 backup files
)

# Enable performance logging for critical components
configure_logging(component="query", level=logging.INFO)
```

## Log Analysis Techniques

Once you have logging set up, you can analyze logs to gain insights into your application's behavior.

### Basic Log Analysis

#### Filtering Logs

Use standard Unix tools to filter logs:

```bash
# Find all error logs
grep "ERROR" activerecord.log

# Find slow queries (taking more than 100ms)
grep "execution time" activerecord.log | grep -E "[0-9]{3,}\.[0-9]+ms"

# Count queries by type
grep "Executing SQL:" activerecord.log | grep -c "SELECT"
grep "Executing SQL:" activerecord.log | grep -c "INSERT"
grep "Executing SQL:" activerecord.log | grep -c "UPDATE"
grep "Executing SQL:" activerecord.log | grep -c "DELETE"
```

#### Analyzing Query Patterns

```bash
# Extract unique query patterns (removing parameter values)
grep "Executing SQL:" activerecord.log | sed -E 's/\[.*\]/[params]/g' | sort | uniq -c | sort -nr
```

### Advanced Log Analysis

#### Using Python for Log Analysis

```python
import re
from collections import defaultdict

# Analyze query frequency and execution time
def analyze_query_logs(log_file):
    query_pattern = re.compile(r"Executing SQL: (.*) with params (.*) \(([0-9.]+)ms\)")
    query_stats = defaultdict(list)
    
    with open(log_file, 'r') as f:
        for line in f:
            match = query_pattern.search(line)
            if match:
                sql, params, time = match.groups()
                # Normalize SQL by replacing literal values with placeholders
                normalized_sql = re.sub(r"'[^']*'", "'?'", sql)
                query_stats[normalized_sql].append(float(time))
    
    # Calculate statistics
    results = []
    for sql, times in query_stats.items():
        results.append({
            'sql': sql,
            'count': len(times),
            'avg_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'total_time': sum(times)
        })
    
    # Sort by total time (most expensive queries first)
    return sorted(results, key=lambda x: x['total_time'], reverse=True)

# Usage
stats = analyze_query_logs('activerecord.log')
for query in stats[:10]:  # Top 10 most expensive queries
    print(f"Query: {query['sql']}")
    print(f"Count: {query['count']}, Avg: {query['avg_time']:.2f}ms, Total: {query['total_time']:.2f}ms")
    print()
```

#### Visualizing Log Data

Use Python libraries like matplotlib or pandas to visualize log data:

```python
import matplotlib.pyplot as plt
import pandas as pd

# Convert query stats to DataFrame
def visualize_query_stats(stats):
    df = pd.DataFrame(stats)
    
    # Plot query frequency
    plt.figure(figsize=(12, 6))
    df.sort_values('count', ascending=False)[:10].plot(kind='bar', x='sql', y='count')
    plt.title('Top 10 Most Frequent Queries')
    plt.tight_layout()
    plt.savefig('query_frequency.png')
    
    # Plot query execution time
    plt.figure(figsize=(12, 6))
    df.sort_values('total_time', ascending=False)[:10].plot(kind='bar', x='sql', y='total_time')
    plt.title('Top 10 Most Time-Consuming Queries')
    plt.tight_layout()
    plt.savefig('query_time.png')

# Usage
visualize_query_stats(stats)
```

## Identifying Performance Bottlenecks

Logs are invaluable for identifying performance bottlenecks in your ActiveRecord application.

### Detecting Slow Queries

```python
import re
from datetime import datetime

def find_slow_queries(log_file, threshold_ms=100):
    slow_queries = []
    timestamp_pattern = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})")
    query_pattern = re.compile(r"Executing SQL: (.*) with params (.*) \(([0-9.]+)ms\)")
    
    with open(log_file, 'r') as f:
        for line in f:
            timestamp_match = timestamp_pattern.search(line)
            query_match = query_pattern.search(line)
            
            if timestamp_match and query_match:
                timestamp = timestamp_match.group(1)
                sql, params, time = query_match.groups()
                time_ms = float(time)
                
                if time_ms > threshold_ms:
                    slow_queries.append({
                        'timestamp': timestamp,
                        'sql': sql,
                        'params': params,
                        'time_ms': time_ms
                    })
    
    return sorted(slow_queries, key=lambda x: x['time_ms'], reverse=True)

# Usage
slow_queries = find_slow_queries('activerecord.log', threshold_ms=100)
for query in slow_queries:
    print(f"[{query['timestamp']}] {query['time_ms']:.2f}ms: {query['sql']}")
    print(f"Params: {query['params']}")
    print()
```

### Identifying N+1 Query Problems

N+1 query problems occur when your code executes N additional queries to fetch related data for N records:

```python
import re
from collections import defaultdict

def detect_n_plus_1(log_file, time_window_seconds=1):
    query_pattern = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3}) .* Executing SQL: (.*) with params (.*)")
    query_groups = []
    current_group = []
    last_timestamp = None
    
    with open(log_file, 'r') as f:
        for line in f:
            match = query_pattern.search(line)
            if match:
                timestamp_str, ms, sql, params = match.groups()
                timestamp = datetime.strptime(f"{timestamp_str}.{ms}", "%Y-%m-%d %H:%M:%S.%f")
                
                if last_timestamp is None:
                    last_timestamp = timestamp
                    current_group.append((timestamp, sql, params))
                elif (timestamp - last_timestamp).total_seconds() <= time_window_seconds:
                    current_group.append((timestamp, sql, params))
                else:
                    if len(current_group) > 5:  # Potential N+1 problem
                        query_groups.append(current_group)
                    current_group = [(timestamp, sql, params)]
                    last_timestamp = timestamp
    
    # Check the last group
    if len(current_group) > 5:
        query_groups.append(current_group)
    
    # Analyze potential N+1 problems
    n_plus_1_candidates = []
    for group in query_groups:
        # Look for patterns where the same query is repeated with different parameters
        normalized_queries = defaultdict(list)
        for timestamp, sql, params in group:
            # Normalize SQL by replacing literal values with placeholders
            normalized_sql = re.sub(r"'[^']*'", "'?'", sql)
            normalized_queries[normalized_sql].append((timestamp, sql, params))
        
        # If a single query pattern appears multiple times, it might be an N+1 problem
        for normalized_sql, instances in normalized_queries.items():
            if len(instances) > 5 and "WHERE" in normalized_sql:
                n_plus_1_candidates.append({
                    'pattern': normalized_sql,
                    'count': len(instances),
                    'examples': instances[:3]  # First 3 examples
                })
    
    return n_plus_1_candidates

# Usage
n_plus_1_problems = detect_n_plus_1('activerecord.log')
for problem in n_plus_1_problems:
    print(f"Potential N+1 problem: {problem['pattern']}")
    print(f"Repeated {problem['count']} times")
    print("Examples:")
    for timestamp, sql, params in problem['examples']:
        print(f"  {sql} with params {params}")
    print()
```

### Analyzing Transaction Performance

```python
import re
from datetime import datetime

def analyze_transactions(log_file):
    transaction_pattern = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3}) .* Transaction (BEGIN|COMMIT|ROLLBACK)")
    transactions = []
    current_transaction = None
    
    with open(log_file, 'r') as f:
        for line in f:
            match = transaction_pattern.search(line)
            if match:
                timestamp_str, ms, action = match.groups()
                timestamp = datetime.strptime(f"{timestamp_str}.{ms}", "%Y-%m-%d %H:%M:%S.%f")
                
                if action == "BEGIN":
                    current_transaction = {'start': timestamp, 'queries': []}
                elif action in ("COMMIT", "ROLLBACK") and current_transaction:
                    current_transaction['end'] = timestamp
                    current_transaction['duration'] = (current_transaction['end'] - current_transaction['start']).total_seconds()
                    current_transaction['action'] = action
                    transactions.append(current_transaction)
                    current_transaction = None
            
            # Capture queries within transaction
            elif current_transaction and "Executing SQL:" in line:
                current_transaction['queries'].append(line.strip())
    
    # Sort by duration (longest first)
    return sorted(transactions, key=lambda x: x['duration'], reverse=True)

# Usage
transactions = analyze_transactions('activerecord.log')
for i, txn in enumerate(transactions[:10]):  # Top 10 longest transactions
    print(f"Transaction {i+1}: {txn['duration']:.6f} seconds ({txn['action']})")
    print(f"Queries: {len(txn['queries'])}")
    if len(txn['queries']) > 0:
        print(f"First query: {txn['queries'][0]}")
        print(f"Last query: {txn['queries'][-1]}")
    print()
```

## Integrating with Monitoring Tools

For production applications, consider integrating your logs with monitoring tools.

### Structured Logging

Use structured logging for better integration with log analysis tools:

```python
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': self.formatTime(record, self.datefmt),
            'name': record.name,
            'level': record.levelname,
            'message': record.getMessage(),
        }
        
        # Add extra attributes
        for key, value in record.__dict__.items():
            if key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
                          'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module',
                          'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                          'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName'):
                log_record[key] = value
        
        return json.dumps(log_record)

# Configure JSON logging
def configure_json_logging():
    logger = logging.getLogger('rhosocial.activerecord')
    handler = logging.FileHandler('activerecord.json.log')
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    return logger

# Usage
json_logger = configure_json_logging()
```

### Integration with ELK Stack

For larger applications, consider using the ELK Stack (Elasticsearch, Logstash, Kibana):

```python
# Configure logging to output in a format compatible with Logstash
configure_logging(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
    file_path="/var/log/myapp/activerecord.log"
)
```

Then configure Logstash to ingest these logs and send them to Elasticsearch for analysis with Kibana.

### Integration with Prometheus

For metrics-based monitoring, consider exposing key metrics from your logs to Prometheus:

```python
from prometheus_client import Counter, Histogram, start_http_server
import time

# Define metrics
query_counter = Counter('activerecord_queries_total', 'Total number of SQL queries', ['query_type'])
query_duration = Histogram('activerecord_query_duration_seconds', 'Query execution time', ['query_type'])
transaction_counter = Counter('activerecord_transactions_total', 'Total number of transactions', ['status'])
transaction_duration = Histogram('activerecord_transaction_duration_seconds', 'Transaction execution time')

# Start Prometheus metrics server
start_http_server(8000)

# Monkey patch ActiveRecord to collect metrics
original_execute = db_connection.execute

def instrumented_execute(sql, params=None):
    query_type = sql.split()[0].upper() if sql else 'UNKNOWN'
    query_counter.labels(query_type=query_type).inc()
    
    start_time = time.time()
    result = original_execute(sql, params)
    duration = time.time() - start_time
    
    query_duration.labels(query_type=query_type).observe(duration)
    return result

db_connection.execute = instrumented_execute
```

## Best Practices for Logging

1. **Log Appropriate Levels**: Use the right log level for each message (DEBUG, INFO, WARNING, ERROR, CRITICAL)

2. **Include Context**: Include relevant context in log messages (user ID, request ID, etc.)

3. **Structured Logging**: Use structured logging formats (JSON) for easier parsing and analysis

4. **Log Rotation**: Configure log rotation to prevent logs from consuming too much disk space

5. **Performance Considerations**: Be mindful of the performance impact of extensive logging

6. **Sensitive Data**: Avoid logging sensitive data (passwords, personal information, etc.)

7. **Correlation IDs**: Use correlation IDs to track requests across multiple components

8. **Regular Analysis**: Regularly analyze logs to identify patterns and issues

9. **Alerting**: Set up alerts for critical log events

10. **Retention Policy**: Define a log retention policy based on your needs and regulatory requirements