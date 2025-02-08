# Performance Problems Guide

This guide covers common performance problems in RhoSocial ActiveRecord applications and their solutions, with examples from social media and e-commerce applications.

## Query Performance

### N+1 Query Problem

```python
# Problem: Multiple queries for related data
# Social Media Example
def get_user_posts():
    # Bad: Generates N+1 queries
    posts = Post.query().all()
    for post in posts:
        # Extra query for each post
        print(f"Author: {post.author.username}")
        # Extra query for each post
        print(f"Comments: {len(post.comments)}")

# Solution: Use eager loading
def get_user_posts_optimized():
    posts = Post.query()\
        .with_('author', 'comments')\
        .all()
    
    for post in posts:
        # No extra queries
        print(f"Author: {post.author.username}")
        print(f"Comments: {len(post.comments)}")

# E-commerce Example
def get_orders():
    # Bad: Multiple queries
    orders = Order.query().all()
    for order in orders:
        # Extra queries
        print(f"Customer: {order.user.name}")
        for item in order.items:
            # More extra queries
            print(f"Product: {item.product.name}")

# Solution
def get_orders_optimized():
    orders = Order.query()\
        .with_('user', 'items.product')\
        .all()
```

### Inefficient Queries

```python
# Problem: Inefficient WHERE clauses
# Bad: Full table scan
users = User.query()\
    .where('LOWER(email) = ?', ('john@example.com',))\
    .all()

# Solution: Use proper indexing and conditions
users = User.query()\
    .where('email = ?', ('john@example.com',))\
    .all()

# Problem: Unnecessary columns
# Bad: Selecting all columns
posts = Post.query().all()

# Solution: Select only needed columns
posts = Post.query()\
    .select('id', 'title', 'created_at')\
    .all()
```

### Query Analysis

```python
class QueryAnalyzer:
    """Analyze query performance."""
    
    def __init__(self):
        self.queries = []
    
    def analyze_query(self, query: 'IQuery'):
        """Analyze query execution."""
        # Get query plan
        plan = query.explain()
        
        # Execute with timing
        start = time.perf_counter()
        result = query.all()
        duration = time.perf_counter() - start
        
        # Store analysis
        self.queries.append({
            'sql': query.to_sql()[0],
            'plan': plan,
            'duration': duration,
            'result_count': len(result)
        })
        
        return result
    
    def print_analysis(self):
        """Print query analysis results."""
        print("\nQuery Analysis Results:")
        for i, query in enumerate(self.queries, 1):
            print(f"\nQuery #{i}")
            print(f"SQL: {query['sql']}")
            print(f"Duration: {query['duration']:.3f}s")
            print(f"Results: {query['result_count']}")
            print("\nExecution Plan:")
            print(query['plan'])

# Usage
analyzer = QueryAnalyzer()

# Analyze user query
users = analyzer.analyze_query(
    User.query()
        .with_('posts')
        .where('status = ?', ('active',))
)

# Analyze order query
orders = analyzer.analyze_query(
    Order.query()
        .with_('items.product')
        .where('status = ?', ('pending',))
)

analyzer.print_analysis()
```

## Memory Problems

### Memory Leaks

```python
# Problem: Memory accumulation
def process_all_users():
    users = []
    offset = 0
    while True:
        batch = User.query()\
            .limit(1000)\
            .offset(offset)\
            .all()
        if not batch:
            break
        users.extend(batch)  # Accumulates memory
        offset += 1000
    return users

# Solution: Process in batches
def process_users_batched():
    def process_batch(users):
        for user in users:
            process_user(user)
    
    offset = 0
    batch_size = 1000
    while True:
        users = User.query()\
            .limit(batch_size)\
            .offset(offset)\
            .all()
        
        if not users:
            break
        
        process_batch(users)
        users = None  # Clear reference
        gc.collect()  # Force garbage collection
        
        offset += batch_size

# Memory-efficient processing
class BatchProcessor:
    """Process large datasets efficiently."""
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
    
    def process_records(self, query: 'IQuery', processor: callable):
        """Process records in batches."""
        offset = 0
        processed = 0
        
        while True:
            # Get batch
            records = query\
                .limit(self.batch_size)\
                .offset(offset)\
                .all()
            
            if not records:
                break
            
            # Process batch
            for record in records:
                processor(record)
                processed += 1
            
            # Clear references
            records = None
            gc.collect()
            
            offset += self.batch_size
        
        return processed

# Usage
processor = BatchProcessor()
def process_order(order):
    # Process single order
    pass

processed_count = processor.process_records(
    Order.query().where('status = ?', ('pending',)),
    process_order
)
```

### Resource Management

```python
class ResourceTracker:
    """Track and manage resource usage."""
    
    def __init__(self):
        self.start_memory = 0
        self.peak_memory = 0
        self.resources = []
    
    def __enter__(self):
        self.start_memory = self.get_memory_usage()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def track_resource(self, resource: Any):
        """Track resource for cleanup."""
        self.resources.append(resource)
    
    def cleanup(self):
        """Clean up tracked resources."""
        for resource in self.resources:
            try:
                if hasattr(resource, 'close'):
                    resource.close()
                elif hasattr(resource, 'cleanup'):
                    resource.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up resource: {e}")
        
        self.resources.clear()
        gc.collect()
    
    def get_memory_usage(self) -> int:
        """Get current memory usage."""
        import psutil
        process = psutil.Process()
        memory = process.memory_info().rss
        self.peak_memory = max(self.peak_memory, memory)
        return memory
    
    def print_stats(self):
        """Print resource usage statistics."""
        current_memory = self.get_memory_usage()
        print("\nResource Usage Statistics:")
        print(f"Initial Memory: {self.start_memory / 1024 / 1024:.1f} MB")
        print(f"Current Memory: {current_memory / 1024 / 1024:.1f} MB")
        print(f"Peak Memory: {self.peak_memory / 1024 / 1024:.1f} MB")
        print(f"Memory Increase: {(current_memory - self.start_memory) / 1024 / 1024:.1f} MB")

# Usage
with ResourceTracker() as tracker:
    # Process large dataset
    processor = BatchProcessor()
    processor.process_records(
        Order.query().with_('items'),
        lambda order: process_order(order)
    )
    
    tracker.print_stats()
```

## Connection Problems

### Connection Pool Issues

```python
class ConnectionMonitor:
    """Monitor database connections."""
    
    def __init__(self):
        self.active_connections = 0
        self.peak_connections = 0
        self.total_operations = 0
        self.operation_times = []
    
    def start_operation(self):
        """Track start of database operation."""
        self.active_connections += 1
        self.peak_connections = max(
            self.peak_connections,
            self.active_connections
        )
        self.total_operations += 1
        return time.perf_counter()
    
    def end_operation(self, start_time: float):
        """Track end of database operation."""
        self.active_connections -= 1
        duration = time.perf_counter() - start_time
        self.operation_times.append(duration)
    
    def print_stats(self):
        """Print connection statistics."""
        print("\nConnection Statistics:")
        print(f"Active Connections: {self.active_connections}")
        print(f"Peak Connections: {self.peak_connections}")
        print(f"Total Operations: {self.total_operations}")
        if self.operation_times:
            avg_time = sum(self.operation_times) / len(self.operation_times)
            print(f"Average Operation Time: {avg_time:.3f}s")

# Usage
monitor = ConnectionMonitor()

def execute_with_monitoring(func):
    start = monitor.start_operation()
    try:
        return func()
    finally:
        monitor.end_operation(start)

# Monitor database operations
result = execute_with_monitoring(
    lambda: User.query().with_('posts').all()
)

monitor.print_stats()
```

### Connection Leaks

```python
class ConnectionTracker:
    """Track database connections."""
    
    def __init__(self):
        self.connections = set()
        self.lock = threading.Lock()
    
    def track_connection(self, connection):
        """Track new connection."""
        with self.lock:
            self.connections.add(connection)
    
    def untrack_connection(self, connection):
        """Untrack closed connection."""
        with self.lock:
            self.connections.remove(connection)
    
    def cleanup_connections(self):
        """Clean up tracked connections."""
        with self.lock:
            for conn in self.connections.copy():
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
            self.connections.clear()
    
    @contextmanager
    def tracked_connection(self):
        """Context manager for connection tracking."""
        connection = create_connection()
        self.track_connection(connection)
        try:
            yield connection
        finally:
            self.untrack_connection(connection)
            connection.close()

# Usage
tracker = ConnectionTracker()

with tracker.tracked_connection() as conn:
    # Use connection
    pass

# Clean up at shutdown
tracker.cleanup_connections()
```

## Best Practices

1. **Query Optimization**
   - Use eager loading
   - Select specific columns
   - Use proper indexes
   - Monitor query performance

2. **Memory Management**
   - Process in batches
   - Clean up resources
   - Monitor memory usage
   - Use efficient queries

3. **Connection Management**
   - Use connection pooling
   - Track connections
   - Clean up properly
   - Monitor usage

4. **Performance Monitoring**
   - Track metrics
   - Analyze patterns
   - Set thresholds
   - Regular review

## Next Steps

1. Learn about [Error Resolution](error_resolution.md)
2. Review [Debugging Guide](debugging_guide.md)
3. Study [Common Issues](common_issues.md)