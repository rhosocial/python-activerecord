# Performance Optimization

This guide covers comprehensive performance optimization strategies for RhoSocial ActiveRecord applications, with examples from social media and e-commerce domains.

## Query Optimization

### Select Specific Fields

```python
# Instead of selecting all fields
users = User.query().all()

# Select only needed fields
users = User.query()\
    .select('id', 'username', 'email')\
    .all()

# E-commerce example
order_summary = Order.query()\
    .select('id', 'total', 'status', 'created_at')\
    .where('user_id = ?', (user_id,))\
    .all()
```

### Eager Loading

```python
# Avoid N+1 queries
posts = Post.query()\
    .with_('author', 'comments.author')\
    .where('created_at > ?', (one_week_ago,))\
    .all()

# E-commerce example
orders = Order.query()\
    .with_('user', 'items.product')\
    .where('status = ?', ('pending',))\
    .order_by('created_at DESC')\
    .all()
```

### Batch Processing

```python
def process_users_in_batches(batch_size: int = 1000):
    """Process users in batches to manage memory."""
    offset = 0
    while True:
        users = User.query()\
            .limit(batch_size)\
            .offset(offset)\
            .all()
        
        if not users:
            break
        
        for user in users:
            process_user(user)
        
        offset += batch_size

# E-commerce batch processing
def update_order_statuses(status: str, batch_size: int = 100):
    """Update order statuses in batches."""
    with Order.transaction():
        Order.query()\
            .where('status = ?', ('pending',))\
            .batch(batch_size, lambda orders: [
                update_order_status(order, status)
                for order in orders
            ])
```

## Caching Strategies

### Query Cache

```python
from functools import lru_cache
from datetime import timedelta

class QueryCache:
    """Query result caching."""
    
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self.cache = {}
        self.timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached result."""
        if key not in self.cache:
            return None
        
        # Check expiration
        timestamp = self.timestamps[key]
        if datetime.now() - timestamp > timedelta(seconds=self.ttl):
            del self.cache[key]
            del self.timestamps[key]
            return None
        
        return self.cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Cache query result."""
        self.cache[key] = value
        self.timestamps[key] = datetime.now()

# Usage
query_cache = QueryCache()

@lru_cache(maxsize=100)
def get_user_stats(user_id: int) -> dict:
    """Get cached user statistics."""
    cache_key = f"user_stats:{user_id}"
    
    # Check cache
    if cached := query_cache.get(cache_key):
        return cached
    
    # Calculate stats
    stats = User.query()\
        .select(
            'COUNT(posts.id) as post_count',
            'COUNT(comments.id) as comment_count'
        )\
        .join('LEFT JOIN posts ON posts.user_id = users.id')\
        .join('LEFT JOIN comments ON comments.user_id = users.id')\
        .where('users.id = ?', (user_id,))\
        .group_by('users.id')\
        .one()
    
    # Cache result
    query_cache.set(cache_key, stats)
    return stats
```

### Model Cache

```python
class ModelCache:
    """Active record model caching."""
    
    def __init__(self, model_class: Type[ActiveRecord], ttl: int = 3600):
        self.model_class = model_class
        self.ttl = ttl
        self.cache = {}
        self.timestamps = {}
    
    def get(self, id: Any) -> Optional[ActiveRecord]:
        """Get cached model instance."""
        if id not in self.cache:
            return None
        
        timestamp = self.timestamps[id]
        if datetime.now() - timestamp > timedelta(seconds=self.ttl):
            del self.cache[id]
            del self.timestamps[id]
            return None
        
        return self.cache[id]
    
    def set(self, instance: ActiveRecord) -> None:
        """Cache model instance."""
        id_value = getattr(instance, instance.primary_key())
        self.cache[id_value] = instance
        self.timestamps[id_value] = datetime.now()
    
    def invalidate(self, id: Any) -> None:
        """Invalidate cached instance."""
        if id in self.cache:
            del self.cache[id]
            del self.timestamps[id]

# Usage
product_cache = ModelCache(Product)

def get_product(product_id: int) -> Product:
    """Get product with caching."""
    if cached := product_cache.get(product_id):
        return cached
    
    product = Product.find_one_or_fail(product_id)
    product_cache.set(product)
    return product
```

## Memory Management

### Resource Cleanup

```python
class ResourceManager:
    """Manage database resources."""
    
    def __init__(self):
        self.resources = []
    
    def register(self, resource: Any):
        """Register resource for cleanup."""
        self.resources.append(resource)
    
    def cleanup(self):
        """Clean up all resources."""
        for resource in self.resources:
            try:
                if hasattr(resource, 'close'):
                    resource.close()
                elif hasattr(resource, 'cleanup'):
                    resource.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up resource: {e}")
        
        self.resources.clear()

# Usage
def process_large_dataset():
    """Process large dataset with resource management."""
    manager = ResourceManager()
    
    try:
        # Open file resource
        file = open('large_data.csv', 'r')
        manager.register(file)
        
        # Process data in chunks
        batch_size = 1000
        while chunk := file.readlines(batch_size):
            process_data_chunk(chunk)
            
    finally:
        manager.cleanup()
```

### Memory-Efficient Queries

```python
class QueryOptimizer:
    """Optimize query memory usage."""
    
    @staticmethod
    def chunk_query(
        query: 'IQuery',
        batch_size: int = 1000,
        callback: Callable[[List[Any]], None]
    ) -> None:
        """Process query results in chunks."""
        offset = 0
        while True:
            batch = query\
                .limit(batch_size)\
                .offset(offset)\
                .all()
            
            if not batch:
                break
            
            callback(batch)
            offset += batch_size
    
    @staticmethod
    def stream_results(
        query: 'IQuery',
        callback: Callable[[Any], None]
    ) -> None:
        """Stream query results one at a time."""
        batch_size = 100
        offset = 0
        
        while True:
            batch = query\
                .limit(batch_size)\
                .offset(offset)\
                .all()
            
            if not batch:
                break
            
            for record in batch:
                callback(record)
            
            offset += batch_size

# Usage
def process_orders():
    """Process orders efficiently."""
    query = Order.query()\
        .where('status = ?', ('pending',))
    
    def process_batch(orders: List[Order]):
        for order in orders:
            process_order(order)
    
    QueryOptimizer.chunk_query(query, callback=process_batch)
```

## Connection Management

### Connection Pooling

```python
class ConnectionPool:
    """Database connection pool."""
    
    def __init__(self, size: int = 5):
        self.size = size
        self.connections = []
        self.available = []
        self.lock = threading.Lock()
    
    def get_connection(self) -> Connection:
        """Get connection from pool."""
        with self.lock:
            # Create new connection if needed
            if not self.available and len(self.connections) < self.size:
                connection = create_connection()
                self.connections.append(connection)
                self.available.append(connection)
            
            # Wait for available connection
            while not self.available:
                time.sleep(0.1)
            
            return self.available.pop()
    
    def release_connection(self, connection: Connection):
        """Return connection to pool."""
        with self.lock:
            self.available.append(connection)
    
    def cleanup(self):
        """Clean up all connections."""
        with self.lock:
            for connection in self.connections:
                connection.close()
            self.connections.clear()
            self.available.clear()

# Usage
class DatabaseManager:
    def __init__(self):
        self.pool = ConnectionPool(size=10)
    
    @contextmanager
    def connection(self):
        """Connection context manager."""
        connection = self.pool.get_connection()
        try:
            yield connection
        finally:
            self.pool.release_connection(connection)
```

### Connection Monitoring

```python
class ConnectionMonitor:
    """Monitor database connections."""
    
    def __init__(self):
        self.active_connections = 0
        self.total_queries = 0
        self.query_times = []
        self.lock = threading.Lock()
    
    def connection_opened(self):
        """Track connection open."""
        with self.lock:
            self.active_connections += 1
    
    def connection_closed(self):
        """Track connection close."""
        with self.lock:
            self.active_connections -= 1
    
    def query_executed(self, duration: float):
        """Track query execution."""
        with self.lock:
            self.total_queries += 1
            self.query_times.append(duration)
    
    def get_stats(self) -> dict:
        """Get connection statistics."""
        with self.lock:
            return {
                'active_connections': self.active_connections,
                'total_queries': self.total_queries,
                'avg_query_time': statistics.mean(self.query_times)
                if self.query_times else 0
            }

# Usage
monitor = ConnectionMonitor()

class MonitoredConnection:
    def __init__(self, connection):
        self.connection = connection
    
    def __enter__(self):
        monitor.connection_opened()
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        monitor.connection_closed()
```

## Best Practices

1. **Query Optimization**
   - Select specific fields
   - Use eager loading
   - Implement batch processing
   - Optimize joins

2. **Caching Strategy**
   - Cache query results
   - Cache model instances
   - Use appropriate TTL
   - Invalidate cache properly

3. **Memory Management**
   - Clean up resources
   - Use memory-efficient queries
   - Process large datasets in chunks
   - Monitor memory usage

4. **Connection Management**
   - Use connection pooling
   - Monitor connections
   - Handle connection errors
   - Clean up properly

5. **Performance Monitoring**
   - Track query times
   - Monitor memory usage
   - Profile database operations
   - Set up alerts

## Next Steps

1. Study [Testing Strategy](testing_strategy.md)
2. Review [Transaction Usage](transaction_usage.md)
3. Learn about [Error Handling](error_handling.md)